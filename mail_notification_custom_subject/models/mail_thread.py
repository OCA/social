# Copyright 2020-2021 Tecnativa - João Marques
# Copyright 2021 Tecnativa - Pedro M. Baeza
# Copyright 2022 Moduon - Eduardo de Miguel
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, models


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    @api.returns("mail.message", lambda value: value.id)
    def message_post(
        self,
        *,
        body="",
        subject=None,
        message_type="notification",
        email_from=None,
        author_id=None,
        parent_id=False,
        subtype_xmlid=None,
        subtype_id=False,
        partner_ids=None,
        attachments=None,
        attachment_ids=None,
        body_is_html=False,
        **kwargs,
    ):
        if subtype_xmlid:
            subtype_id = self.env["ir.model.data"]._xmlid_to_res_id(
                subtype_xmlid,
                raise_if_not_found=False,
            )
        if not subtype_id:
            subtype_id = self.env["ir.model.data"]._xmlid_to_res_id("mail.mt_note")
        if subtype_id:
            custom_subjects = (
                self.env["mail.message.custom.subject"]
                .sudo()
                .search(
                    [
                        ("model_id.model", "=", self._name),
                        ("subtype_ids", "=", subtype_id),
                    ]
                )
                .sudo(False)
            )
            if not subject:
                subject = "Re: %s" % self.env["mail.message"].with_context(
                    default_model=self._name,
                    default_res_id=self.id,
                )._get_record_name({})
            for template in custom_subjects:
                try:
                    rendered_subject_template = self.env[
                        "mail.template"
                    ]._render_template(
                        template_src=template.subject_template,
                        model=self._name,
                        res_ids=[self.id],
                    )[self.id]
                    if template.position == "replace":
                        subject = rendered_subject_template
                    elif template.position == "append_before":
                        subject = rendered_subject_template + subject
                    elif template.position == "append_after":
                        subject += rendered_subject_template
                except Exception:
                    rendered_subject_template = False
        return super().message_post(
            body=body,
            subject=subject,
            message_type=message_type,
            email_from=email_from,
            author_id=author_id,
            parent_id=parent_id,
            subtype_xmlid=subtype_xmlid,
            subtype_id=subtype_id,
            partner_ids=partner_ids,
            attachments=attachments,
            attachment_ids=attachment_ids,
            body_is_html=body_is_html,
            **kwargs,
        )
