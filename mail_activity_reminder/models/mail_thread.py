from odoo import models


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    def _get_notify_valid_parameters(self):
        """Inherit method to add notif_layout in the set of valid parameters"""

        notif_parameters = super()._get_notify_valid_parameters()
        # Added notif_layout in the set of valid parameter
        return notif_parameters | {"notif_layout"}
