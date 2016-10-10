# -*- coding: utf-8 -*-
# © 2016 ACSONE SA/NV <https://acsone.eu>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from openerp import models, api
from openerp import tools
from openerp.tools.translate import _


class MailNotification(models.Model):

    _inherit = 'mail.notification'

    @api.model
    def _get_partner_names(self, partner_ids):
        """
        :type partner_ids: [integer]
        :param partner_ids: ids of the partner followers
        :rparam: list of the partner'name that are also a user or having
        notify_email attribute not none
        """
        partners = self.env['res.partner'].browse(partner_ids)
        partners_name = [
            partner.name for partner in partners if
            partner.user_ids or partner.notify_email != 'none'
        ]
        return partners_name

    @api.model
    def get_signature_footer(
            self, user_id, res_model=None, res_id=None, user_signature=True):
        """
        Override this method to add name of notified partners into the mail
        footer
        """
        footer = super(MailNotification, self).get_signature_footer(
            user_id, res_model=res_model, res_id=res_id,
            user_signature=user_signature)
        partner_ids = self.env.context.get('partners_to_notify')
        if footer and partner_ids:
            partners_name = self._get_partner_names(partner_ids)
            additional_footer = u'<br /><small>%s%s.</small><br />' %\
                (_('Also notified: '),
                 ', '.join(partners_name))
            footer = tools.append_content_to_html(
                additional_footer, footer, plaintext=False,
                container_tag='div')

        return footer

    @api.model
    def _notify(
            self, message_id, partners_to_notify=None, force_send=False,
            user_signature=True):
        ctx = self.env.context.copy()
        if not self.env.context.get('mail_notify_noemail'):
            ctx.update({
                'partners_to_notify': partners_to_notify,
            })
        return super(MailNotification, self.with_context(ctx))._notify(
            message_id,
            partners_to_notify=partners_to_notify,
            force_send=force_send, user_signature=user_signature)
