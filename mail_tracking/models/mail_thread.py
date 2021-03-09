# Copyright 2019 Alexandre Díaz
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from email.utils import getaddresses

from lxml import etree

from odoo import _, api, fields, models
from odoo.tools import email_split_and_format


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    failed_message_ids = fields.One2many(
        "mail.message",
        "res_id",
        string="Failed Messages",
        domain=lambda self: [("model", "=", self._name)]
        + self._get_failed_message_domain(),
    )

    def _get_failed_message_domain(self):
        """Domain used to display failed messages on the 'failed_messages'
           widget"""
        failed_states = self.env["mail.message"].get_failed_states()
        return [
            ("mail_tracking_needs_action", "=", True),
            ("mail_tracking_ids.state", "in", list(failed_states)),
        ]

    @api.model
    def _message_route_process(self, message, message_dict, routes):
        """Adds CC recipient to the message.

        Because Odoo implementation avoid store 'from, to, cc' recipients we
        ensure that this information its written into the mail.message record.
        """
        message_dict.update(
            {
                "email_cc": message_dict.get("cc", False),
                "email_to": message_dict.get("to", False),
            }
        )
        return super()._message_route_process(message, message_dict, routes)

    def _message_get_suggested_recipients(self):
        """Adds email 'extra' recipients as suggested recipients.

        If the recipient has a res.partner, use it.
        """
        res = super()._message_get_suggested_recipients()
        self._add_extra_recipients_suggestions(res, "email_cc", _("Cc"))
        self._add_extra_recipients_suggestions(res, "email_to", _("Anon. To"))
        return res

    def _add_extra_recipients_suggestions(self, suggestions, field_mail, reason):
        ResPartnerObj = self.env["res.partner"]
        aliases = self.env["mail.alias"].get_aliases()
        email_extra_formated_list = []
        for record in self:
            emails_extra = record.message_ids.mapped(field_mail)
            for email in emails_extra:
                email_extra_formated_list.extend(email_split_and_format(email))
        email_extra_formated_list = set(email_extra_formated_list)
        email_extra_list = [x[1] for x in getaddresses(email_extra_formated_list)]
        partners_info = self._message_partner_info_from_emails(email_extra_list)
        for pinfo in partners_info:
            partner_id = pinfo["partner_id"]
            email = pinfo["full_name"]
            if not partner_id:
                if email not in aliases:
                    self._message_add_suggested_recipient(
                        suggestions, email=email, reason=reason
                    )
            else:
                partner = ResPartnerObj.browse(partner_id)
                self._message_add_suggested_recipient(
                    suggestions, partner=partner, reason=reason
                )

    @api.model
    def _fields_view_get(
        self, view_id=None, view_type="form", toolbar=False, submenu=False
    ):
        """Add filters for failed messages.

        These filters will show up on any form or search views of any
        model inheriting from ``mail.thread``.
        """
        res = super()._fields_view_get(
            view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu
        )
        if view_type not in {"search", "form"}:
            return res
        doc = etree.XML(res["arch"])
        if view_type == "search":
            # Modify view to add new filter element
            nodes = doc.xpath("//search")
            if nodes:
                # Create filter element
                new_filter = etree.Element(
                    "filter",
                    {
                        "string": _("Failed sent messages"),
                        "name": "failed_message_ids",
                        "domain": str(
                            [
                                [
                                    "failed_message_ids.mail_tracking_ids.state",
                                    "in",
                                    list(self.env["mail.message"].get_failed_states()),
                                ],
                                [
                                    "failed_message_ids.mail_tracking_needs_action",
                                    "=",
                                    True,
                                ],
                            ]
                        ),
                    },
                )
                nodes[0].append(etree.Element("separator"))
                nodes[0].append(new_filter)
        elif view_type == "form":
            # Modify view to add new field element
            nodes = doc.xpath("//field[@name='message_ids' and @widget='mail_thread']")
            if nodes:
                # Create field
                field_failed_messages = etree.Element(
                    "field",
                    {"name": "failed_message_ids", "widget": "mail_failed_message"},
                )
                nodes[0].addprevious(field_failed_messages)
        res["arch"] = etree.tostring(doc, encoding="unicode")
        return res
