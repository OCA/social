# -*- coding: utf-8 -*-
from odoo import models, api


class MailThread(models.AbstractModel):
    _inherit = 'mail.thread'

    @api.multi
    def message_get_recipient_values(self, notif_message=None, recipient_ids=None):
        """ Get specific notification recipient values to store on the notification
        mail_mail. Basic method just set the recipient partners as mail_mail
        recipients. Inherit this method to add custom behavior like using
        recipient email_to to bypass the recipint_ids heuristics in the
        mail sending mechanism. """
        return {
            # 'recipient_ids': [(4, pid) for pid in recipient_ids]
            'recipient_ids': [(6, 0, recipient_ids)]
        }