# -*- coding: utf-8 -*-
# License AGPL-3: Antiun Ingenieria S.L. - Antonio Espinosa
# See README.rst file on addon root folder for more details

import json
import threading

from openerp import models, api


class MailMail(models.Model):
    _inherit = 'mail.mail'

    def _mandrill_headers_add(self):
        for mail in self.sudo():
            headers = {}
            if mail.headers:
                try:
                    headers.update(eval(mail.headers))
                except Exception:
                    pass

            metadata = {
                'odoo_db': getattr(threading.currentThread(), 'dbname', None),
                'odoo_model': mail.model,
                'odoo_id': mail.res_id,
            }
            headers['X-MC-Metadata'] = json.dumps(metadata)
            mail.headers = repr(headers)
        return True

    @api.multi
    def send(self, auto_commit=False, raise_exception=False):
        self._mandrill_headers_add()
        super(MailMail, self).send(
            auto_commit=auto_commit,
            raise_exception=raise_exception)
        return True
