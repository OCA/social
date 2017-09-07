# coding: utf-8
# © 2017 David BEAL @ Akretion
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging
from odoo import models

_logger = logging.getLogger(__name__)

try:
    from premailer import transform
except (ImportError, IOError) as err:
    _logger.debug(err)


class MailTemplate(models.Model):
    _inherit = 'mail.template'

    def generate_email(self, res_ids, fields=None):
        res = super(MailTemplate, self).generate_email(res_ids, fields=fields)
        for id in res:
            if res[id].get('body_html'):
                res[id]['body_html'] = transform(res[id]['body_html'])
        return res
