# -*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2016 Compassion CH (http://www.compassion.ch)
#    Releasing children from poverty in Jesus' name
#    @author: Emanuel Cino <ecino@compassion.ch>
#
#    The licence is in the file __openerp__.py
#
##############################################################################

from openerp import models, fields, api


class EmailComposeMessage(models.TransientModel):
    """ Email message sent through SendGrid """
    _inherit = 'mail.compose.message'

    body_sendgrid = fields.Html(compute='_compute_sendgrid_view')

    @api.depends('body')
    def _compute_sendgrid_view(self):
        for wizard in self:
            template = wizard.template_id
            sendgrid_template = template.sendgrid_localized_template
            res_id = self.env.context.get('active_id')
            render_body = self.render_template_batch(
                wizard.body, wizard.model, [res_id], post_process=True)[res_id]
            if sendgrid_template and wizard.body:
                wizard.body_sendgrid = sendgrid_template.html_content.replace(
                    '<%body%>', render_body)
            else:
                wizard.body_sendgrid = render_body

    @api.model
    def render_message_batch(self, wizard, res_ids):
        """ Attach sendgrid template to e-mail and render substitutions """
        template_values = super(
            EmailComposeMessage, self).render_message_batch(wizard, res_ids)
        template = wizard.template_id
        substitutions = template.substitution_ids.filtered(
            lambda s: s.lang == self.env.context.get('lang'))
        sendgrid_template_id = template.sendgrid_localized_template.id

        for substitution in substitutions:
            substitution_values = template.render_template_batch(
                substitution.value, template.model, res_ids)
            for res_id in res_ids:
                template_values[res_id].setdefault(
                    'substitution_ids', list()).append((0, 0, {
                        'key': substitution.key,
                        'value': substitution_values[res_id]}))

        for value in template_values.itervalues():
            value['sendgrid_template_id'] = sendgrid_template_id

        return template_values
