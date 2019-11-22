# Copyright 2019 Eficent Business and IT Consulting Services, S.L.
#                <https//www.eficent.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    disable_notify_mail_drop_target = fields.Boolean(
        'Disable Notification followers on mail dropped to a Thread',
        help="When this setting is set, when a user drops an "
             "email into an existing thread the followers of the thread will "
             "not be notified. This sets an ir.config.parameter "
             "mail_drop_target.disable_notify")

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()

        disable_notify_mail_drop_target = \
            self.env["ir.config_parameter"].get_param(
                "mail_drop_target.disable_notify", default=False)
        res.update(
            disable_notify_mail_drop_target=disable_notify_mail_drop_target,
        )
        return res

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        self.env['ir.config_parameter'].set_param(
            "mail_drop_target.disable_notify",
            self.disable_notify_mail_drop_target or '')
