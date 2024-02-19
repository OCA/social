# Copyright Nguyen Minh Chien (chien@trobz.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import base64
import os

from odoo import api, models


class IrAttachment(models.Model):
    _inherit = "ir.attachment"

    def _get_email_file_extensions(self):
        return ["msg", "eml"]

    def _process_email_file_msg(self, res_obj, raw_content):
        if not hasattr(res_obj, "message_process_msg"):
            return False
        message = base64.b64encode(raw_content)
        thread_id = res_obj.message_process_msg(
            res_obj._name, message, thread_id=res_obj.id
        )
        return thread_id

    @api.model
    def _process_email_file_default(self, res_obj, raw_content):
        if not hasattr(res_obj, "message_drop"):
            return False
        message = raw_content
        thread_id = res_obj.message_drop(res_obj._name, message, thread_id=res_obj.id)
        return thread_id

    def read_mail_file_content(self, file_name, raw_content, res_id, res_model):
        file_extensions = self._get_email_file_extensions()
        name_lst = os.path.splitext(file_name)
        file_extension = name_lst[-1].lower().replace(".", "")
        if not file_extension or file_extension not in file_extensions:
            return False

        res_obj = self.env[res_model].browse(res_id)
        if not res_obj:
            return False

        handler = "_process_email_file_{}".format(file_extension)
        if not hasattr(self, handler):
            handler = "_process_email_file_default"

        res = getattr(self, handler)(res_obj, raw_content)
        return res
