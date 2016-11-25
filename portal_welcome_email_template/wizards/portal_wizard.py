# -*- coding: utf-8 -*-
# (c) 2015 Incaser Informatica S.L. - Sergio Teruel
# (c) 2015 Incaser Informatica S.L. - Carlos Dauden
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

from openerp import models, api


class WizardUser(models.TransientModel):
    _inherit = 'portal.wizard.user'

    @api.multi
    def _send_email(self):
        user = self.user_id
        portal_url = user.partner_id.with_context(
            lang=user.lang,
            signup_force_type_in_url=''
        )._get_signup_url_for_action()[user.partner_id.id]
        user.partner_id.with_context(
            lang=user.lang, signup_force_type_in_url='').signup_prepare()

        template = self.env.ref(
            'portal_welcome_email_template.portal_welcome_email')

        ctx = self.env.context.copy()
        ctx.update({
            'login': user.login,
            'portal_url': portal_url,
            'db': self.env.cr.dbname,
            'portal': self.wizard_id.portal_id.name,
            'signup_url': user.signup_url,
            'welcome_message': self.wizard_id.welcome_message or '',
        })
        return template.with_context(ctx).send_mail(user.id)
