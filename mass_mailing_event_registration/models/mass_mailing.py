# -*- coding: utf-8 -*-
# License AGPL-3: Antiun Ingenieria S.L. - Javier Iniesta
# See README.rst file on addon root folder for more details

from openerp import models, api
from openerp.tools.translate import _


class MassMailing(models.Model):
    _inherit = 'mail.mass_mailing'

    @api.model
    def _get_mailing_model(self):
        res = super(MassMailing, self)._get_mailing_model()
        res.append(('event.registration', _('Event Registrations')))
        return res
