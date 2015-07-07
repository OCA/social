# -*- coding: utf-8 -*-
##############################################################################
# (c) 2015 Pedro M. Baeza
# License AGPL-3 - See LICENSE file on root folder for details
##############################################################################
from openerp import models, fields, api


class MailComposeMessage(models.TransientModel):
    _inherit = 'mail.compose.message'

    lang = fields.Many2one(
        comodel_name="res.lang", string="Force language")

    @api.multi
    def onchange_lang(
            self, lang, template_id, composition_mode, model, res_id):
        res = {}
        if lang:
            lang = self.env['res.lang'].browse(lang)
            obj = self.with_context(force_lang=lang.code)
            res = obj.onchange_template_id(
                composition_mode=composition_mode, model=model,
                template_id=template_id, res_id=res_id)
        return res
