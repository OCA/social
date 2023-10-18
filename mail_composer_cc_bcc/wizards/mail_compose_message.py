# Copyright 2023 Camptocamp
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import Command, api, fields, models, tools

CC_BCC_FIELDS = {
    "email_cc": "partner_cc_ids",
    "email_bcc": "partner_bcc_ids",
}


class MailComposeMessage(models.TransientModel):
    _inherit = "mail.compose.message"

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

    partner_cc_ids = fields.Many2many(
        "res.partner",
        "mail_compose_message_res_partner_cc_rel",
        "wizard_id",
        "partner_id",
        string="Cc",
    )
    partner_bcc_ids = fields.Many2many(
        "res.partner",
        "mail_compose_message_res_partner_bcc_rel",
        "wizard_id",
        "partner_id",
        string="Bcc",
    )

    def _onchange_template_id(self, template_id, composition_mode, model, res_id):
        if not template_id:
            return {"value": {}}
        ctx = {"is_from_composer": True}
        ctx.update(self.env.context)
        self_ctx = self.with_context(**ctx)
        res = super(MailComposeMessage, self_ctx)._onchange_template_id(
            template_id, composition_mode, model, res_id
        )
        res_ids = [res_id]
        # tpl_partners_only need to be False for email_cc value
        tmpl_ctx = self.env["mail.template"].with_context(tpl_partners_only=False)
        mail_tmpl = tmpl_ctx.browse(template_id)
        template_values = mail_tmpl.generate_email(res_ids, CC_BCC_FIELDS)
        values = template_values[res_id]
        for fname in CC_BCC_FIELDS:
            value = values.get(fname, None)
            if not value:
                continue
            self._set_partner_field(CC_BCC_FIELDS[fname], value)
        return res

    def _set_partner_field(self, field_name, email):
        if field_name not in CC_BCC_FIELDS.values():
            return
        for_email = [("email", "in", tools.email_split(email))]
        partner = self.env["res.partner"].search(for_email)
        current_partners = getattr(self, field_name)
        setattr(self, field_name, current_partners + partner)

    def _action_send_mail(self, auto_commit=False):
        # don't impact mass_mailing that also uses mail.compose.message
        if self.composition_mode == "mass_mail":
            return super()._action_send_mail(auto_commit)
        context = {
            "is_from_composer": True,
            "partner_cc_ids": self.partner_cc_ids,
            "partner_bcc_ids": self.partner_bcc_ids,
        }
        context.update(self.env.context)
        self_super = super(MailComposeMessage, self.with_context(**context))
        res = self_super._action_send_mail(auto_commit)
        return res
