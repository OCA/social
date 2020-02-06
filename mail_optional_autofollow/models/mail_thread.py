# Copyright 2020 ABF OSIELL <http://osiell.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class MailThread(models.AbstractModel):
    _inherit = 'mail.thread'

    @api.multi
    @api.returns('mail.message', lambda value: value.id)
    def message_post(
            self, body='', subject=None, message_type='notification',
            subtype=None, parent_id=False, attachments=None,
            notif_layout=False, add_sign=True, model_description=False,
            mail_auto_delete=True, **kwargs):
        return super(MailThread, self.with_context(
            mail_post_autofollow=self.env.context.get(
                'mail_post_autofollow_override', self.env.context.get(
                    'mail_post_autofollow', True)))).message_post(
                        body=body, subject=subject, message_type=message_type,
                        subtype=subtype, parent_id=parent_id,
                        attachments=attachments, notif_layout=notif_layout,
                        add_sign=add_sign, model_description=model_description,
                        mail_auto_delete=mail_auto_delete, **kwargs)
