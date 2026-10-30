# Copyright 2024 Dixmit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.osv import expression
from odoo.tools import SQL

from odoo.addons.mail.tools.discuss import Store


class ResPartner(models.Model):
    """Update of res.partner class to take into account the gateway."""

    _inherit = "res.partner"

    gateway_channel_ids = fields.One2many(
        "res.partner.gateway.channel", inverse_name="partner_id"
    )

    @api.readonly
    @api.model
    def search_for_channel_invite(self, search_term, channel_id=None, limit=30):
        channel = (
            self.env["discuss.channel"].browse(int(channel_id)) if channel_id else None
        )
        if not channel or channel.channel_type != "gateway":
            return super().search_for_channel_invite(
                search_term, channel_id=channel_id, limit=limit
            )
        gateway_group = self.env.ref("mail_gateway.gateway_user")
        domain = expression.AND(
            [
                expression.OR(
                    [
                        [("name", "ilike", search_term)],
                        [("email", "ilike", search_term)],
                    ]
                ),
                [("active", "=", True)],
                [("user_ids", "!=", False)],
                [("user_ids.active", "=", True)],
                [("user_ids.share", "=", False)],
                [("channel_ids", "not in", channel.id)],
                # only users allowed to access gateway channels can be invited to them
                [("user_ids.groups_id", "in", gateway_group.id)],
            ]
        )
        query = self._search(domain, limit=limit)
        # bypass lack of support for case insensitive order in search()
        query.order = SQL(
            'LOWER(%s), "res_partner"."id"', self._field_to_sql(self._table, "name")
        )
        store = Store()
        self.env["res.partner"].browse(query)._search_for_channel_invite_to_store(
            store, channel
        )
        return {
            "count": self.env["res.partner"].search_count(domain),
            "data": store.get_result(),
        }

    def _get_channels_as_member(self):
        channels = super()._get_channels_as_member()
        if self.env.user.has_group("mail_gateway.gateway_user"):
            channels |= self.env["discuss.channel"].search(
                [
                    ("channel_type", "=", "gateway"),
                    (
                        "channel_member_ids",
                        "in",
                        self.env["discuss.channel.member"]
                        .sudo()
                        ._search(
                            [
                                ("partner_id", "=", self.id),
                                ("is_pinned", "=", True),
                            ]
                        ),
                    ),
                ]
            )
        return channels

    def _to_store(self, store: Store, /, *, fields=None, **kwargs):
        """Override to add the gateway channels the partner can be reached on."""
        super()._to_store(store, fields=fields, **kwargs)
        if fields is None:
            fields = ["gateway_channels"]
        if "gateway_channels" not in fields:
            return
        # sudo: res.partner.gateway.channel - technical data needed by the web
        # client, not meant to be restricted by the reader's access rights
        for partner in self.sudo():
            store.add(
                partner,
                {"gateway_channels": partner.gateway_channel_ids.mail_format()},
            )


class ResPartnerGatewayChannel(models.Model):
    _name = "res.partner.gateway.channel"
    _description = "Technical data used to get the gateway author"

    name = fields.Char(related="gateway_id.name")
    partner_id = fields.Many2one(
        "res.partner", required=True, readonly=True, ondelete="cascade"
    )
    gateway_id = fields.Many2one(
        "mail.gateway", required=True, readonly=True, ondelete="cascade"
    )
    gateway_token = fields.Char(readonly=True)
    company_id = fields.Many2one(
        "res.company", related="gateway_id.company_id", store=True
    )

    @api.depends_context("mail_gateway_partner_info")
    def _compute_display_name(self):
        # Be able to tell to which partner belongs the gateway partner channel
        # e.g.: picking it from a selector
        if not self.env.context.get("mail_gateway_partner_info"):
            return super()._compute_display_name()
        for gateway_channel in self:
            gateway_channel.display_name = (
                f"{gateway_channel.partner_id.display_name} ({gateway_channel.name})"
            )

    _sql_constraints = [
        (
            "unique_partner_gateway",
            "UNIQUE(partner_id, gateway_id)",
            "Partner can only have one configuration for each gateway.",
        ),
    ]

    def mail_format(self):
        return [r._mail_format() for r in self]

    def _mail_format(self):
        return {
            "id": self.id,
            "name": self.name,
            "gateway": {
                "id": self.gateway_id.id,
                "name": self.gateway_id.name,
                "type": self.gateway_id.gateway_type,
            },
        }
