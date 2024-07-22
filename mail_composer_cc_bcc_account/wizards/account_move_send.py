# Copyright 2024 Camptocamp
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).


from odoo import Command, api, fields, models, tools


class AccountMoveSend(models.TransientModel):
    _inherit = "account.move.send"

    partner_cc_ids = fields.Many2many(
        "res.partner",
        "account_move_send_res_partner_cc_rel",
        "wizard_id",
        "partner_id",
        string="Cc",
        compute="_compute_mail_partner_cc_bcc_ids",
        store=True,
        readonly=False,
    )
    partner_bcc_ids = fields.Many2many(
        "res.partner",
        "account_move_send_res_partner_bcc_rel",
        "wizard_id",
        "partner_id",
        string="Bcc",
        compute="_compute_mail_partner_cc_bcc_ids",
        store=True,
        readonly=False,
    )

    def _get_partner_ids_from_mail(self, move, emails):
        partners = self.env["res.partner"].with_company(move.company_id)
        for mail_data in tools.email_split(emails):
            partners |= partners.find_or_create(mail_data)
        return partners

    @api.model
    def default_get(self, fields_list):
        company = self.env.company
        res = super().default_get(fields_list)
        partner_cc = company.default_partner_cc_ids
        if partner_cc:
            res["partner_cc_ids"] = [Command.set(partner_cc.ids)]
        partner_bcc = company.default_partner_bcc_ids
        if partner_bcc:
            res["partner_bcc_ids"] = [Command.set(partner_bcc.ids)]
        return res

    @api.depends("mail_template_id")
    def _compute_mail_partner_cc_bcc_ids(self):
        for wizard in self:
            if wizard.mode == "invoice_single" and wizard.mail_template_id:
                wizard.partner_cc_ids = self._get_partner_ids_from_mail(
                    wizard.move_ids, wizard.mail_template_id.email_cc
                )
                wizard.partner_bcc_ids = self._get_partner_ids_from_mail(
                    wizard.move_ids, wizard.mail_template_id.email_bcc
                )
            else:
                wizard.partner_cc_ids = None
                wizard.partner_bcc_ids = None

    def _get_mail_move_values(self, move, wizard=None):
        mail_template_id = (
            move.send_and_print_values
            and move.send_and_print_values.get("mail_template_id")
        )
        mail_template = (
            wizard
            and wizard.mail_template_id
            or self.env["mail.template"].browse(mail_template_id)
        )
        mail_lang = self._get_default_mail_lang(move, mail_template)
        return {
            "mail_template_id": mail_template,
            "mail_lang": mail_lang,
            "mail_body": wizard
            and wizard.mail_body
            or self._get_default_mail_body(move, mail_template, mail_lang),
            "mail_subject": wizard
            and wizard.mail_subject
            or self._get_default_mail_subject(move, mail_template, mail_lang),
            "mail_partner_ids": wizard
            and wizard.mail_partner_ids
            or self._get_default_mail_partner_ids(move, mail_template, mail_lang),
            "mail_attachments_widget": wizard
            and wizard.mail_attachments_widget
            or self._get_default_mail_attachments_widget(move, mail_template),
            "partner_cc_ids": wizard
            and wizard.partner_cc_ids
            or self._get_default_mail_partner_cc_ids(move, mail_template),
            "partner_bcc_ids": wizard
            and wizard.partner_bcc_ids
            or self._get_default_mail_partner_bcc_ids(move, mail_template),
        }

    # -------------------------------------------------------------------------
    # BUSINESS ACTIONS
    # -------------------------------------------------------------------------

    @api.model
    def _send_mail(self, move, mail_template, **kwargs):
        """Send the journal entry passed as parameter by mail."""
        partner_ids = kwargs.get("partner_ids", [])
        move_with_context = move.with_context(
            no_new_invoice=True,
            mail_notify_author=self.env.user.partner_id.id in partner_ids,
            is_from_composer=True,
            partner_cc_ids=self.partner_cc_ids,
            partner_bcc_ids=self.partner_bcc_ids,
        )
        extra_args = {
            "email_layout_xmlid": "mail.mail_notification_layout_with_responsible_signature",  # noqa: E501
            "email_add_signature": not mail_template,
            "mail_auto_delete": mail_template.auto_delete,
            "mail_server_id": mail_template.mail_server_id.id,
            "reply_to_force_new": False,
            "message_type": "comment",
        }
        kwargs.update(extra_args)
        new_message = move_with_context.message_post(**kwargs)
        # Prevent duplicated attachments linked to the invoice.
        new_message.attachment_ids.write(
            {
                "res_model": new_message._name,
                "res_id": new_message.id,
            }
        )
