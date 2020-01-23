from odoo import api, models
from odoo.tools.safe_eval import safe_eval


class MailThread(models.AbstractModel):
    _inherit = 'mail.thread'

    @api.multi
    def _message_add_suggested_recipient(
            self, result, partner=None, email=None, reason=''):
        result = super(MailThread, self)._message_add_suggested_recipient(
            result, partner=partner, email=email, reason=reason)
        domain = self.env[
            'mail.wizard.invite'
        ]._mail_restrict_follower_selection_get_domain()
        eval_domain = safe_eval(domain)
        for key in result:
            for partner_id, email, reason in result[key]:
                if partner_id:
                    partner = self.env['res.partner'].search(
                        [('id', '=', partner_id)] + eval_domain
                    )
                    if not partner:
                        result[key].remove((partner_id, email, reason))
        return result
