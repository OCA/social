# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, ValidationError

from ..social_advertising_utils import ADVERTISING_ENVIRONMENTS


class SocialAdvertisingAccount(models.Model):
    """Advertising account of a social media, as the social media reports it.

    These records mirror what the social media answers: the connector
    modules create and refresh them and nothing is ever pushed back. The
    user only picks which one the campaigns and the ads of a
    ``social.account`` belong to, with :meth:`action_set_current`.

    Only the fields every advertising platform has are declared here. What
    belongs to a single social media, such as the serving status of
    LinkedIn, is added by its connector module.
    """

    _name = "social.advertising.account"
    _description = "Social Advertising Account"
    _order = "is_current desc, name, id"

    account_id = fields.Many2one(
        "social.account",
        required=True,
        index=True,
        ondelete="cascade",
    )
    company_id = fields.Many2one(
        related="account_id.company_id",
        store=True,
        index=True,
    )
    media_id = fields.Many2one(related="account_id.media_id", store=True)
    name = fields.Char(required=True)
    remote_ref = fields.Char(
        string="Remote Reference",
        required=True,
        index=True,
        copy=False,
        help="Identifier of the advertising account on the social media.",
    )
    environment = fields.Selection(
        ADVERTISING_ENVIRONMENTS,
        required=True,
        help="Environment this advertising account belongs to. A test "
        "advertising account is never served nor billed.",
    )
    currency_id = fields.Many2one(
        "res.currency",
        help="Currency the budgets of this advertising account are denominated in.",
    )
    is_current = fields.Boolean(
        string="In Use",
        copy=False,
        help="Advertising account the campaigns and the ads of this social "
        "media account work with. Only one at a time.",
    )
    web_url = fields.Char(
        string="Campaign Manager URL",
        compute="_compute_web_url",
        help="Address of this advertising account on the social media.",
    )
    last_sync_date = fields.Datetime(string="Last Fetch", readonly=True)
    campaign_ids = fields.One2many(
        "social.advertising.campaign", "advertising_account_id"
    )
    campaign_count = fields.Integer(compute="_compute_campaign_count")
    campaign_group_ids = fields.One2many(
        "social.advertising.campaign.group", "advertising_account_id"
    )
    campaign_group_count = fields.Integer(compute="_compute_campaign_group_count")

    _sql_constraints = [
        (
            "remote_ref_account_uniq",
            "unique(account_id, remote_ref)",
            "An advertising account can only be linked once to a social "
            "media account.",
        ),
    ]

    @api.depends("campaign_ids")
    def _compute_campaign_count(self):
        counts = dict(
            self.env["social.advertising.campaign"]._read_group(
                domain=[("advertising_account_id", "in", self.ids)],
                groupby=["advertising_account_id"],
                aggregates=["__count"],
            )
        )
        for advertising_account in self:
            advertising_account.campaign_count = counts.get(advertising_account, 0)

    @api.depends("campaign_group_ids")
    def _compute_campaign_group_count(self):
        counts = dict(
            self.env["social.advertising.campaign.group"]._read_group(
                domain=[("advertising_account_id", "in", self.ids)],
                groupby=["advertising_account_id"],
                aggregates=["__count"],
            )
        )
        for advertising_account in self:
            advertising_account.campaign_group_count = counts.get(
                advertising_account, 0
            )

    def action_open_campaigns(self):
        """Open the campaigns of this advertising account."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Campaigns"),
            "res_model": "social.advertising.campaign",
            "view_mode": "tree,form",
            "domain": [("advertising_account_id", "=", self.id)],
            "context": {"default_advertising_account_id": self.id},
        }

    def action_open_campaign_groups(self):
        """Open the campaign groups of this advertising account."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Campaign Groups"),
            "res_model": "social.advertising.campaign.group",
            "view_mode": "tree,form",
            "domain": [("advertising_account_id", "=", self.id)],
            "context": {"default_advertising_account_id": self.id},
        }

    @api.depends("remote_ref", "media_id.media_type")
    def _compute_web_url(self):
        """Leave the address empty: each connector builds its own."""
        for advertising_account in self:
            advertising_account.web_url = False

    def _get_display_reference(self):
        """Return the reference shown next to the name.

        The remote reference is returned as it is: how it is shortened, if at
        all, depends on the format of each social media, so a connector
        overrides this.
        """
        self.ensure_one()
        return self.remote_ref or ""

    @api.depends("name", "remote_ref")
    def _compute_display_name(self):
        """Show the reference: advertising accounts often share a name."""
        for advertising_account in self:
            identifier = advertising_account._get_display_reference()
            advertising_account.display_name = (
                f"{advertising_account.name} ({identifier})"
                if identifier
                else advertising_account.name
            )

    @api.constrains("is_current", "environment", "account_id")
    def _check_is_current(self):
        """Only one advertising account per social media account is in use.

        The environment of the two must match as well: the social media
        never answers the entities of the other one, so an advertising
        account of the wrong environment can only be a mistake.
        """
        environments = dict(
            self._fields["environment"]._description_selection(self.env)
        )
        for advertising_account in self.filtered("is_current"):
            account = advertising_account.account_id
            if advertising_account.environment != account.environment:
                raise ValidationError(
                    _(
                        "The advertising account %(advertising_account)s "
                        "belongs to the %(advertising_environment)s "
                        "environment, while the account %(account)s is set "
                        "to %(environment)s.",
                        advertising_account=advertising_account.display_name,
                        advertising_environment=environments.get(
                            advertising_account.environment
                        ),
                        account=account.display_name,
                        environment=environments.get(account.environment),
                    )
                )
            if (
                self.search_count(
                    [
                        ("account_id", "=", account.id),
                        ("is_current", "=", True),
                    ]
                )
                > 1
            ):
                raise ValidationError(
                    _(
                        "The account %(account)s can only work with one "
                        "advertising account at a time.",
                        account=account.display_name,
                    )
                )

    def _set_current(self):
        """Make this advertising account the one the campaigns work with.

        Only one advertising account of a social media account is in use, so
        the others are unset in the same operation. Written with ``sudo()``:
        a regular user reads the advertising accounts but never writes them.
        """
        self.ensure_one()
        others = self.sudo().search(
            [
                ("account_id", "=", self.account_id.id),
                ("id", "!=", self.id),
                ("is_current", "=", True),
            ]
        )
        others.write({"is_current": False})
        self.sudo().write({"is_current": True})

    def action_set_current(self):
        """Choose this advertising account from the account form."""
        self.ensure_one()
        if not self.account_id.can_manage_account:
            raise AccessError(
                _(
                    "Only the responsible user of the account %(account)s and "
                    "the social media administrators may choose its "
                    "advertising account.",
                    account=self.account_id.display_name,
                )
            )
        self._set_current()
