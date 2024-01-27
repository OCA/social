# Copyright 2023 Camptocamp
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import Command, api, fields, models, tools, _


class MailComposeMessage(models.TransientModel):
    _inherit = "mail.compose.message"

    partner_cc_ids = fields.Many2many(
        "res.partner",
        "mail_compose_message_res_partner_cc_rel",
        "wizard_id",
        "partner_id",
        string="Cc",
        compute="_compute_partner_cc_ids",
        readonly=False,
        store=True,
    )
    partner_bcc_ids = fields.Many2many(
        "res.partner",
        "mail_compose_message_res_partner_bcc_rel",
        "wizard_id",
        "partner_id",
        string="Bcc",
        compute="_compute_partner_bcc_ids",
        readonly=False,
        store=True,
    )

    # ------------------------------------------------------------
    # SET DEFAULT VALUES FOR CC, BCC
    # ------------------------------------------------------------

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

    @api.depends("template_id")
    def _compute_partner_bcc_ids(self):
        partners = self.env["res.partner"]
        for composer in self:
            if composer.template_id:
                for mail_data in tools.email_split(composer.template_id.email_bcc):
                    composer.partner_bcc_ids |= partners.find_or_create(mail_data)
            else:
                composer.partner_bcc_ids = None

    @api.depends("template_id")
    def _compute_partner_cc_ids(self):
        partners = self.env["res.partner"]
        for composer in self:
            if composer.template_id:
                for mail_data in tools.email_split(composer.template_id.email_cc):
                    composer.partner_cc_ids |= partners.find_or_create(mail_data)
            else:
                composer.partner_cc_ids = None

    @api.depends(
        "composition_mode",
        "model",
        "parent_id",
        "res_domain",
        "res_ids",
        "template_id",
        "partner_cc_ids",
        "partner_bcc_ids",
    )
    def _compute_partner_ids(self):
        """
        Change:
            add email_bcc
            recompute when change template/ manually input in composer

        return: field Recipients filled with value from 'email_cc', 'email_to', 'partner_ids', 'email_bcc'
        """
        for composer in self:
            if (
                composer.template_id
                and composer.composition_mode == "comment"
                and not composer.composition_batch
            ):
                res_ids = composer._evaluate_res_ids() or [0]
                rendered_values = composer._generate_template_for_composer(
                    res_ids,
                    {"email_cc", "email_to", "partner_ids", "email_bcc"},
                    find_or_create_partners=True,
                )[res_ids[0]]
                if rendered_values.get("partner_ids"):
                    composer.partner_ids = rendered_values["partner_ids"]
                    if composer.partner_cc_ids:
                        composer.partner_ids |= composer.partner_cc_ids
                    if composer.partner_bcc_ids:
                        composer.partner_ids |= composer.partner_bcc_ids
            elif composer.parent_id and composer.composition_mode == "comment":
                composer.partner_ids = composer.parent_id.partner_ids
            elif not composer.template_id:
                composer.partner_ids = False

    # ------------------------------------------------------------
    # RENDERING / VALUES GENERATION
    # ------------------------------------------------------------

    def _prepare_mail_values_rendered(self, res_ids):
        """
        add cc and bcc when send to mail.message
        """
        mail_values = super()._prepare_mail_values_rendered(res_ids)

        for res_id in mail_values:
            mail_values[res_id].update(
                {
                    "recipient_cc_ids": self.partner_cc_ids.ids,
                    "recipient_bcc_ids": self.partner_bcc_ids.ids,
                }
            )
        return mail_values

    # ------------------------------------------------------------
    # ACTIONS
    # ------------------------------------------------------------

    def _action_send_mail(self, auto_commit=False):
        """
        Add context is_from_composer when composition_mode == 'comment'
        """
        result_mails_su, result_messages = (
            self.env["mail.mail"].sudo(),
            self.env["mail.message"],
        )

        for wizard in self:
            if wizard.res_domain:
                search_domain = wizard._evaluate_res_domain()
                search_user = wizard.res_domain_user_id or self.env.user
                res_ids = (
                    self.env[wizard.model]
                    .with_user(search_user)
                    .search(search_domain)
                    .ids
                )
            else:
                res_ids = wizard._evaluate_res_ids()
            # in comment mode: raise here as anyway message_post will raise.
            if not res_ids and wizard.composition_mode == "comment":
                raise ValueError(
                    _(
                        "Mail composer in comment mode should run on at least one record. No records found (model %(model_name)s).",
                        model_name=wizard.model,
                    )
                )

            if wizard.composition_mode == "mass_mail":
                result_mails_su += wizard._action_send_mail_mass_mail(
                    res_ids, auto_commit=auto_commit
                )
            else:
                context = {
                    "is_from_composer": True,
                }
                result_messages += wizard.with_context(
                    context
                )._action_send_mail_comment(res_ids)

        return result_mails_su, result_messages
