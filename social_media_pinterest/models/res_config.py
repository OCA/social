# -*- coding: utf-8 -*-
# © 2016 Diagram Software S.L.
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html
from openerp.models import TransientModel
from openerp import fields


class WebsiteConfigSettings(TransientModel):

    _inherit = 'website.config.settings'

    social_pinterest = fields.Char('Pinterest Account',
                                   related='website_id.social_pinterest')
