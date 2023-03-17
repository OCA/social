# Copyright 2023 Solvti sp. z o.o. (https://solvti.pl)
# License LGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import base64

from odoo import api, fields, models

from odoo.addons.base.models.ir_mail_server import extract_rfc2822_addresses


class IrMailServer(models.Model):
    _inherit = "ir.mail_server"

    @api.model
    def send_email(self, message, *args, **kwargs):
        res = super().send_email(message, *args, **kwargs)
        try:
            self._generate_eml_attachment_for_email(message)
        except Exception:
            pass
        return res

    def _generate_eml_attachment_for_email(self, message):
        def _get_header_value(text):
            res = [value for item, value in message._headers if item == text]
            return res

        object_ref = _get_header_value("X-Odoo-Objects")
        if not object_ref:
            return
        res_model, res_id = object_ref[0].split("-")
        models = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("mail.save.attachment.eml.models", "")
        )
        if res_model in models.split(","):
            recipient = extract_rfc2822_addresses(_get_header_value("To"))
            name = f"{recipient[0] if recipient else res_model + res_id}"
            self.env["ir.attachment"].create(
                {
                    "name": f"{name}-{fields.Date.today().strftime('%d%m%y')}.eml",
                    "type": "binary",
                    "datas": base64.b64encode(bytes(message)),
                    "res_model": res_model,
                    "res_id": int(res_id),
                    "mimetype": message._default_type,
                }
            )
