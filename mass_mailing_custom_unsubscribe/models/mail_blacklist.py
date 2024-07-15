# Copyright 2019 Tecnativa - Ernesto Tejeda
# Copyright 2024 Tecnativa - David Vidal
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from markupsafe import Markup

from odoo import fields, models


class MailBlackList(models.Model):
    _inherit = "mail.blacklist"

    metadata = fields.Text()

    def _get_metadata_message(self, message):
        if message and self.env.context.get("metadata"):
            return Markup(
                f"{str(message)}<br/><br/><strong>METADATA</strong><hr/>"
                f"<pre>{self.env.context.get('metadata')}</pre>"
            )

    def _add(self, email, message=None):
        metadata_msg = self._get_metadata_message(message)
        if message and metadata_msg:
            message = metadata_msg
            self.metadata = self.env.context.get("metadata")
        return super()._add(email, message)

    def _remove(self, email, message=None):
        metadata_msg = self._get_metadata_message(message)
        if message and metadata_msg:
            message = metadata_msg
            self.metadata = self.env.context.get("metadata")
        return super()._remove(email, message)
