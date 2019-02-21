# -*- coding: utf-8 -*-
# Copyright 2018 Therp BV <https://therp.nl>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from odoo import api, fields, models


class MailTemplate(models.Model):
    """ In order for the mass email templates to be picked up by the js they
    need to be formatted in a specific way, this is what we do here.
    """
    _inherit = 'mail.template'

    view_id = fields.Many2one('ir.ui.view', ondelete='restrict', readonly=1)

    def _get_wrapped_body_html(self, body_html=None):
        """
        This function is supposed to be used on the body_html of a newly
        created template, it purpose is to wrap the body_html with an xpath
        tag in order to be picked up by the snippet.editor widget.
        """
        final = """<xpath expr="//div[@id='email_designer_themes']"
            position="inside">"
        """
        final += body_html if body_html else self.body_html
        final += '</xpath>'
        return final

    @api.model
    def create(self, vals):
        """
        If a mail template for the mail_mass_mailing model is created, create
        a ir_ui_view qweb record that will be used as a mass_mailing template.
        """
        if vals.get('model_id') == self.env.ref(
                'mass_mailing.model_mail_mass_mailing').id:
            arch = self._get_wrapped_body_html(vals.get('body_html'))
            view_id = self.env['ir.ui.view'].create({
                'arch': arch,
                'type': 'qweb',
                'inherit_id': self.env.ref(
                    'mass_mailing.email_designer_snippets').id,
            })
            vals['view_id'] = view_id.id
        return super(MailTemplate, self).create(vals)

    @api.multi
    def write(self, vals):
        """
        If the user tries to change the model of an already existing template,
        we create the corresponding ir_ui_view qweb record (if not existing)
        and we modify it's arch so that it is picked up correctly.
        """
        model_id = vals.get('model_id')
        if model_id and self.env['ir.model'].browse(
                model_id).model == 'mail.mass_mailing':
            body_html = vals.get('body_html')
            body_html = body_html if body_html else self.body_html
            new_body = self._get_wrapped_body_html(body_html)
            if self.view_id:
                self.view_id.write({'arch': new_body})
            else:
                self.view_id.create({
                    'arch': new_body,
                    'type': 'qweb',
                    'inherit_id': self.env.ref(
                        'mass_mailing.email_designer_snippets').id,
                    })
        # if they changed the model of a template that has as model the mass
        # mailing model, go ahead and delete that view.
        mass_mailing_model = self.env.ref(
            'mass_mailing.model_mail_mass_mailing')
        if model_id and model_id != mass_mailing_model.id:
            self.filtered(
                lambda x: x.model_id.id == mass_mailing_model.id).mapped(
                'view_id').unlink()
        return super(MailTemplate, self).write(vals)

    @api.multi
    def unlink(self):
        view_ids = self.mapped('view_id')
        self.write({'view_id': None})
        view_ids.unlink()
        return super(MailTemplate, self).unlink()
