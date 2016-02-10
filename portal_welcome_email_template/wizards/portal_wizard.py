# -*- coding: utf-8 -*-
# (c) 2015 Incaser Informatica S.L. - Sergio Teruel
# (c) 2015 Incaser Informatica S.L. - Carlos Dauden
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

from openerp import models, api
from openerp import exceptions
from openerp.tools.translate import _


class WizardUser(models.TransientModel):
    """
        A model to configure users in the portal wizard.
    """
    _inherit = 'portal.wizard.user'

    @api.model
    def _send_email(self, wizard_user):
        """ send notification email to a new portal user
            @param wizard_user: browse record of model portal.wizard.user
            @return: the id of the created mail.mail record
        """
        this_context = self._context
        this_user = self.env['res.users'].sudo().browse(self._uid)
        if not this_user.email:
            raise exceptions.Warning(
                _('Email Required'),
                _('You must have an email address in your User Preferences to '
                  'send emails.'))

        # determine subject and body in the portal user's language
        user = self.sudo()._retrieve_user(wizard_user)
        context = dict(this_context or {}, lang=user.lang)
        ctx_portal_url = dict(context, signup_force_type_in_url='')
        portal_url = user.partner_id.with_context(
            ctx_portal_url)._get_signup_url_for_action()[user.partner_id.id]
        user.partner_id.with_context(context).signup_prepare()

        template = self.env.ref(
            'portal_welcome_email_template.portal_welcome_email')
        ctx = this_context.copy()
        ctx.update({
            'login': user.login,
            'portal_url': portal_url,
            'db': self._cr.dbname,
            'portal': wizard_user.wizard_id.portal_id.name,
            'signup_url': user.signup_url,
            'welcome_message': wizard_user.wizard_id.welcome_message or "",
        })
        result = template.with_context(ctx).generate_email_batch(
            template.id, [user.id])[user.id]
        return self.env['mail.mail'].with_context(this_context).create(result)
