# Copyright 2020 Tecnativa - Carlos Roca
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models


class Notification(models.Model):
    _inherit = 'mail.notification'

    def unlink(self):
        if self.env.context.get('unlink_is_read'):
            self.write({"is_read": True})
        else:
            return super().unlink()
