# Copyright (C) 2015 Therp BV <http://therp.nl>
# Copyright (C) 2017 Komit <http://www.komit-consulting.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from lxml import etree
from odoo import api, models


class MailWizardInvite(models.TransientModel):
    _inherit = 'mail.wizard.invite'

    @api.model
    def _mail_restrict_follower_selection_get_domain(self):
        parameter_name = 'mail_restrict_follower_selection.domain'
        return self.env['ir.config_parameter'].sudo().get_param(
            "{0}.{1}".format(parameter_name,
                             self.env.context.get('default_res_model')),
            self.env['ir.config_parameter'].sudo().get_param(
                parameter_name, default='[]')
        )

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False,
                        submenu=False):
        result = super(MailWizardInvite, self).fields_view_get(
            view_id=view_id, view_type=view_type, toolbar=toolbar,
            submenu=submenu)
        arch = etree.fromstring(result['arch'])
        for field in arch.xpath('//field[@name="partner_ids"]'):
            field.attrib['domain'] = self\
                ._mail_restrict_follower_selection_get_domain()
        result['arch'] = etree.tostring(arch)
        return result
