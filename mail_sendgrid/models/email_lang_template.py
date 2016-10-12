# -*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2016 Compassion CH (http://www.compassion.ch)
#    Releasing children from poverty in Jesus' name
#    @author: Emanuel Cino
#
#    The licence is in the file __openerp__.py
#
##############################################################################

from openerp import models, fields


class LanguageTemplate(models.Model):
    """ This class is the relation between and email_template object
    and a sendgrid_template. It allows to specify a different
    sendgrid_template for any selected language.
    """
    _name = 'sendgrid.email.lang.template'

    email_template_id = fields.Many2one('email.template', 'E-mail Template')
    lang = fields.Selection('_lang_get', 'Language', required=True)
    sendgrid_template_id = fields.Many2one(
        'sendgrid.template', 'Sendgrid Template', required=True)

    def _lang_get(self):
        languages = self.env['res.lang'].search([])
        return [(language.code, language.name) for language in languages]
