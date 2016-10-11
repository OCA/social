# -*- coding: utf-8 -*-
##############################################################################
# (c) 2015 Pedro M. Baeza
# License AGPL-3 - See LICENSE file on root folder for details
##############################################################################
from odoo import models, fields, api


class MailComposeMessage(models.TransientModel):
    _inherit = 'mail.compose.message'

    lang = fields.Many2one(
        comodel_name="res.lang", string="Force language")

    @api.onchange('lang', 'template_id')
    def onchange_template_id_wrapper(self):
        """
        Trigger the onchange with special context key.

        This context key will trigger a rebrowse with the correct language
        of the template in the get_email_template function of the mail.template
        model
        """
        self.ensure_one()
        lang = self.lang.code
        values = self.with_context(force_lang=lang).onchange_template_id(
            self.template_id.id, self.composition_mode,
            self.model, self.res_id)['value']
        for fname, value in values.iteritems():
            setattr(self, fname, value)
