# Copyright 2020-2021 Tecnativa - João Marques
# Copyright 2021 Tecnativa - Pedro M. Baeza
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, models


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    @api.returns("mail.message", lambda value: value.id)
    def message_post(
        self,
        body="",
        subject=None,
        message_type="notification",
        subtype=None,
        parent_id=False,
        attachments=None,
        notif_layout=False,
        add_sign=True,
        model_description=False,
        mail_auto_delete=True,
        **kwargs
    ):
        subtype_id = kwargs.get('subtype_id', False)
        if not subtype_id:
            subtype = subtype or 'mt_note'
            if '.' not in subtype:
                subtype = 'mail.%s' % subtype
            subtype_id = self.env['ir.model.data'].xmlid_to_res_id(
                subtype, raise_if_not_found=False,
            )
        if subtype_id:
            custom_subjects = self.env["mail.message.custom.subject"].search(
                [
                    ("model_id.model", "=", self._name),
                    ("subtype_ids", "=", subtype_id),
                ]
            )
            if not subject:
                subject = 'Re: %s' % self.env["mail.message"].with_context(
                    default_model=self._name,
                    default_res_id=self.id,
                )._get_record_name({})
            for template in custom_subjects:
                try:
                    rendered_subject_template = self.env[
                        "mail.template"
                    ]._render_template(
                        template_txt=template.subject_template,
                        model=self._name,
                        res_ids=self.id,
                    )
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
            subtype=subtype,
            parent_id=parent_id,
            attachments=attachments,
            notif_layout=notif_layout,
            add_sign=add_sign,
            model_description=model_description,
            mail_auto_delete=mail_auto_delete,
            **kwargs
        )
