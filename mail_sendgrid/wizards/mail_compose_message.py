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
            render_body = self.render_template(
                wizard.body, wizard.model, [res_id], post_process=True)[res_id]
            if sendgrid_template and wizard.body:
                wizard.body_sendgrid = sendgrid_template.html_content.replace(
                    '<%body%>', render_body)
            else:
                wizard.body_sendgrid = render_body

    @api.multi
    def get_mail_values(self, res_ids):
        """ Attach sendgrid template to e-mail and render substitutions """
        mail_values = super(EmailComposeMessage, self).get_mail_values(res_ids)
        template = self.template_id
        sendgrid_template_id = template.sendgrid_localized_template.id

        if sendgrid_template_id:
            substitutions = template.render_substitutions(res_ids)

            for res_id, value in mail_values.iteritems():
                value['sendgrid_template_id'] = sendgrid_template_id
                value['substitution_ids'] = substitutions[res_id]

        return mail_values
