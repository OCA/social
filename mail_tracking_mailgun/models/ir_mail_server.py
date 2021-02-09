# -*- coding: utf-8 -*-
# Copyright 2016 Tecnativa - Antonio Espinosa
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import json
from odoo import models


class IrMailServer(models.Model):
    _inherit = "ir.mail_server"

    def _tracking_headers_add(self, tracking_email_id, headers):
        headers = super(IrMailServer, self)._tracking_headers_add(
            tracking_email_id, headers)
        headers = headers or {}
        metadata = {
            'odoo_db': self.env.cr.dbname,
            'tracking_email_id': tracking_email_id,
        }
        headers['X-Mailgun-Variables'] = json.dumps(metadata)
        return headers
