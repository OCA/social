# -*- coding: utf-8 -*-
##############################################################################
# (c) 2015 Pedro M. Baeza
# License AGPL-3 - See LICENSE file on root folder for details
##############################################################################
from openerp import models, api


class Report(models.Model):
    _inherit = 'report'

    @api.model
    def translate_doc(self, doc_id, model, lang_field, template, values):
        if self.env.context.get('force_lang'):
            obj = self.with_context(lang=self.env.context['force_lang'],
                                    translatable=True)
        else:
            obj = self
        return super(Report, obj).translate_doc(
            doc_id, model, lang_field, template, values)
