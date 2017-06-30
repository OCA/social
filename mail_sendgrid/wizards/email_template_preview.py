# -*- coding: utf-8 -*-
# Copyright 2015-2017 Compassion CH (http://www.compassion.ch)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, api


class EmailTemplatePreview(models.TransientModel):
    """ Put the preview inside sendgrid template """
    _inherit = 'email_template.preview'

    @api.multi
    def on_change_res_id(self, res_id):
        result = super(EmailTemplatePreview, self).on_change_res_id(res_id)
        body_html = result['value']['body_html']
        template_id = self.env.context.get('template_id')
        template = self.env['sendgrid'].browse(template_id)
        sendgrid_template = template.sendgrid_localized_template
        if sendgrid_template:
            body_html = sendgrid_template.html_content.replace(
                '<%body%>', body_html)
            result['value']['body_html'] = body_html
        return result
