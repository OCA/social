# -*- coding: utf-8 -*-
# Copyright 2016-2017 Compassion CH (http://www.compassion.ch)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields


class LanguageTemplate(models.Model):
    """ This class is the relation between and email_template object
    and a sendgrid_template. It allows to specify a different
    sendgrid_template for any selected language.
    """
    _name = 'sendgrid.email.lang.template'

    email_template_id = fields.Many2one('mail.template', 'E-mail Template')
    lang = fields.Selection('_select_lang', 'Language', required=True)
    sendgrid_template_id = fields.Many2one(
        'sendgrid.template', 'Sendgrid Template', required=True)

    def _select_lang(self):
        languages = self.env['res.lang'].search([])
        return [(language.code, language.name) for language in languages]
