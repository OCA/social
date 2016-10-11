# -*- coding: utf-8 -*-
##############################################################################
# (c) 2015 Pedro M. Baeza
# License AGPL-3 - See LICENSE file on root folder for details
##############################################################################
from odoo import models, api


class MailTemplate(models.Model):
    _inherit = 'mail.template'

    @api.model
    def get_email_template(self, res_ids):
        """
        Rebrowse a template with force_lang context key if it is set.
        """
        if self.ids and res_ids and self.env.context.get('force_lang'):
            self.ensure_one()  # keep behaviour consistent with super function
            template = self.with_context(lang=self.env.context['force_lang'])
            return dict.fromkeys(res_ids, template)
        else:
            return super(MailTemplate, self).get_email_template(res_ids)
