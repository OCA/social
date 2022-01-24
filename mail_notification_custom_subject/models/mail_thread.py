# Copyright 2020-2021 Tecnativa - João Marques
# Copyright 2021 Tecnativa - Pedro M. Baeza
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
        channel_ids=None,
        attachments=None,
        attachment_ids=None,
        add_sign=True,
        record_name=False,
        **kwargs
    ):
        if not subtype_id and subtype_xmlid:
            subtype_id = self.env["ir.model.data"].xmlid_to_res_id(
                subtype_xmlid,
                raise_if_not_found=False,
            )
        if subtype_id:
            custom_subjects = self.env["mail.message.custom.subject"].search(
                [("model_id.model", "=", self._name), ("subtype_ids", "=", subtype_id)]
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
                    )[
                        self.id
                    ]
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
            channel_ids=channel_ids,
            attachments=attachments,
            attachment_ids=attachment_ids,
            add_sign=add_sign,
            record_name=record_name,
            **kwargs,
        )
