# -*- coding: utf-8 -*-
# © 2017 Therp BV <http://therp.nl>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from openerp import models
from openerp.addons.mail_activity.models.mail_activity_mixin import \
    setup_mail_actitivities


@setup_mail_actitivities
class CrmLead(models.Model):
    _inherit = 'crm.lead'
