from odoo import api, fields, models


class MailComposeMessage(models.TransientModel):
    _inherit = 'mail.compose.message'

    @api.multi
    def get_mail_values(self, res_ids):
        """Generate the values that will be used by send_mail to create mail_messages
        or mail_mails. """
        results = super(MailComposeMessage, self).get_mail_values(res_ids)

        for res_id in res_ids:
            results[res_id]['mail_activity_type_id'] = self.mail_activity_type_id.id
        return results
