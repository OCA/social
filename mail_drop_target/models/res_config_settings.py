# Copyright 2019-20 ForgeFlow S.L. (https://www.forgeflow.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    disable_notify_mail_drop_target = fields.Boolean(
        "Disable Notification followers on mail dropped to a Thread",
        config_parameter="mail_drop_target.disable_notify",
        help="When this setting is set, when a user drops an "
        "email into an existing thread the followers of the thread will "
        "not be notified. This sets an ir.config.parameter "
        "mail_drop_target.disable_notify",
    )
