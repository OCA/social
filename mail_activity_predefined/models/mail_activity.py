# Copyright 2021 Hunki Enterprises BV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, exceptions, models


class MailActivity(models.Model):
    _inherit = "mail.activity"

    @api.constrains("res_id", "res_model_id")
    def _constrain_mail_activity_predefined(self):
        """Enforce conditions on mail activities"""
        if not self.env.user.has_group(
            "mail_activity_predefined.group_mail_activity_predefined"
        ):
            return
        for this in self:
            if not this.activity_type_id.predefined:
                continue
            record = self.env[this.res_model].browse(this.res_id)
            if not record._mail_activity_predefined_condition(this.activity_type_id):
                raise exceptions.ValidationError(
                    _("The condition for activity %s does not allow it on %s")
                    % (this.activity_type_id.name, record.display_name)
                )
