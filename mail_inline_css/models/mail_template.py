# Copyright 2017 David BEAL @ Akretion
# Copyright 2019 Camptocamp SA

# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, models

try:
    from premailer import transform
except (ImportError, IOError) as err:
    import logging
    _logger = logging.getLogger(__name__)
    _logger.debug(err)


class MailTemplate(models.Model):
    _inherit = 'mail.template'

    @api.multi
    def generate_email(self, res_ids, fields=None):
        """Use `premailer` to convert styles to inline styles."""
        result = super().generate_email(res_ids, fields=fields)
        if isinstance(res_ids, int):
            result['body_html'] = transform(result['body_html'])
        else:
            for __, data in result.items():
                data['body_html'] = transform(data['body_html'])
        return result
