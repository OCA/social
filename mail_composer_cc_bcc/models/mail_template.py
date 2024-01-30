# Copyright 2023 Camptocamp
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).


import itertools

from odoo import fields, models, tools


class MailTemplate(models.Model):
    _inherit = "mail.template"

    email_bcc = fields.Char(
        "Bcc", help="Blind cc recipients (placeholders may be used here)"
    )

    # ------------------------------------------------------------
    # MESSAGE/EMAIL VALUES GENERATION
    # ------------------------------------------------------------

    def _generate_template_recipients(
        self, res_ids, render_fields, find_or_create_partners=False, render_results=None
    ):
        ModelSudo = self.env[self.model].with_prefetch(res_ids).sudo()

        res = super()._generate_template_recipients(
            res_ids,
            render_fields,
            find_or_create_partners=find_or_create_partners,
            render_results=render_results,
        )

        if "email_bcc" in render_fields and not (self.use_default_to and self.model):
            generated_field_values = self._render_field("email_bcc", res_ids)
            for res_id in res_ids:
                res.setdefault(res_id, {})["email_bcc"] = generated_field_values[res_id]

        if find_or_create_partners:
            res_id_to_company = {}
            if self.model and "company_id" in ModelSudo._fields:
                for read_record in ModelSudo.browse(res_ids).read(["company_id"]):
                    company_id = (
                        read_record["company_id"][0]
                        if read_record["company_id"]
                        else False
                    )
                    res_id_to_company[read_record["id"]] = company_id

            all_emails = []
            email_to_res_ids = {}
            email_to_company = {}
            for res_id in res_ids:
                record_values = res.setdefault(res_id, {})
                mails = tools.email_split(record_values.pop("email_bcc", ""))
                all_emails += mails
                record_company = res_id_to_company.get(res_id)
                for mail in mails:
                    email_to_res_ids.setdefault(mail, []).append(res_id)
                    if record_company:
                        email_to_company[mail] = record_company

            if all_emails:
                customers_information = ModelSudo.browse(
                    res_ids
                )._get_customer_information()
                partners = self.env["res.partner"]._find_or_create_from_emails(
                    all_emails,
                    additional_values={
                        email: {
                            "company_id": email_to_company.get(email),
                            **customers_information.get(email, {}),
                        }
                        for email in itertools.chain(all_emails, [False])
                    },
                )
                for original_email, partner in zip(all_emails, partners):
                    if not partner:
                        continue
                    for res_id in email_to_res_ids[original_email]:
                        res[res_id].setdefault("partner_ids", []).append(partner.id)

        # update 'partner_to' rendered value to 'partner_ids'
        all_partner_to = {
            pid
            for record_values in res.values()
            for pid in self._parse_partner_to(record_values.get("partner_to", ""))
        }
        existing_pids = set()
        if all_partner_to:
            existing_pids = set(
                self.env["res.partner"].sudo().browse(list(all_partner_to)).exists().ids
            )
        for res_id, record_values in res.items():
            partner_to = record_values.pop("partner_to", "")
            if partner_to:
                tpl_partner_ids = (
                    set(self._parse_partner_to(partner_to)) & existing_pids
                )
                record_values.setdefault("partner_ids", []).extend(tpl_partner_ids)

        return res

    def _generate_template(self, res_ids, render_fields, find_or_create_partners=False):
        res = super()._generate_template(
            res_ids, render_fields, find_or_create_partners=find_or_create_partners
        )

        for _lang, (template, template_res_ids) in self._classify_per_lang(
            res_ids
        ).items():
            if "email_bcc" in render_fields:
                template._generate_template_recipients(
                    template_res_ids,
                    set("email_bcc"),
                    render_results=res,
                    find_or_create_partners=find_or_create_partners,
                )
        return res
