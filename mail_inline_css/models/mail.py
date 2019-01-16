# Copyright 2017 David BEAL @ Akretion
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
        res = super().generate_email(res_ids, fields=fields)
        if 'body_html' in res:
            res['body_html'] = transform(res['body_html'])
        return res
