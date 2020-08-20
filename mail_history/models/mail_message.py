# Copyright 2020 Tecnativa - Carlos Roca
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, models


class Message(models.Model):
    _inherit = 'mail.message'

    @api.multi
    def message_format(self):
        """Override this method to add the notification fetching for the read messages.
        """
        vals = super().message_format()
        read_notifs = self.env['mail.notification'].sudo().search(
            [
                ('mail_message_id', 'in', self.ids),
                ('res_partner_id', '!=', False),
                ('is_read', '=', True),
            ]
        )
        # Obtain partners per message
        notif_dict = {}
        for notif in read_notifs:
            mid = notif.mail_message_id.id
            notif_dict.setdefault(mid, [])
            notif_dict[mid].append(
                notif.res_partner_id.id
            )
        # Fill history partner ids field
        for message in vals:
            if message['id'] in notif_dict:
                message.update({
                    'history_partner_ids': notif_dict[
                        message['id']
                    ],
                })
        return vals

    @api.model
    def mark_all_as_read(self, channel_ids=None, domain=None):
        """Override this method for injecting a context key for avoiding the removal of
        mail.notification. We need to inject as well a true leaf in the domain for
        avoiding a part of code in super that removes the records by sql.
        """
        if not domain:
            domain = [['id', '!=', False]]
        return super(
            Message, self.with_context(unlink_is_read=True)
        ).mark_all_as_read(channel_ids=channel_ids, domain=domain)

    @api.multi
    def set_message_done(self):
        """Override this method for injecting a context key for avoiding the removal of
        mail.notification.
        """
        return super(
            Message, self.with_context(unlink_is_read=True)
        ).set_message_done()
