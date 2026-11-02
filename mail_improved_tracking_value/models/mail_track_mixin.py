# Copyright 2018-2022 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import json

from odoo import models


class MailTrackMixin(models.AbstractModel):
    _inherit = "mail.track.mixin"

    def _create_mail_tracking_values(
        self, initial_value, new_value, col_name, col_info
    ):
        """Store the ids of tracked x2many changes as JSON lists."""
        values = super()._create_mail_tracking_values(
            initial_value, new_value, col_name, col_info
        )
        if col_info["type"] in ("many2many", "one2many"):
            values["old_value_text"] = json.dumps(
                initial_value.ids if initial_value else []
            )
            values["new_value_text"] = json.dumps(new_value.ids if new_value else [])
        return values
