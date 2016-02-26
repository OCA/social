# -*- coding: utf-8 -*-
# © 2016 Incaser Informatica S.L. - Sergio Teruel
# © 2016 Incaser Informatica S.L. - Carlos Dauden
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

from openerp import models, fields


class WebsiteMailSippetResponsive(models.TransientModel):
    _name = 'website.config.settings'
    _inherit = ['website.config.settings']

    mail_button_color = fields.Char(related='website_id.mail_button_color')
