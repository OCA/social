# Copyright 2024 Binhex (<https://binhex.cloud>)
# Copyright 2024 Binhex Ariel Barreiros
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

from odoo import api, fields, models


class MailActivity(models.Model):
    _inherit = "mail.activity"

    def _default_is_module_calendar_installed(self):
        module = self.env["ir.module.module"].sudo().search([("name", "=", "calendar")])
        return True if module and module.state == "installed" else False

    user_ids = fields.Many2many(
        "res.users",
        string="Assigned Users",
        help="Activities will be created for this list of users",
    )
    is_multiple_users_activity = fields.Boolean(string="Multiple users activity?")
    is_module_calendar_installed = fields.Boolean(
        readonly=True, default=_default_is_module_calendar_installed
    )

    @api.model_create_multi
    def _create(self, values):
        res = super(MailActivity, self)._create(values)
        if res.user_id in res.user_ids:
            res.user_ids = [(3, res.user_id.id)]
        if res.is_multiple_users_activity:
            res.is_multiple_users_activity = False
            for user in res.user_ids:
                self.create(
                    {
                        "res_model_id": res.res_model_id.id,
                        "res_id": res.res_id,
                        "activity_type_id": res.activity_type_id.id,
                        "date_deadline": res.date_deadline,
                        "user_id": user.id,
                        "summary": res.summary,
                        "note": res.note,
                    }
                )
        return res

    @api.onchange("user_ids")
    def _onchange_user_ids(self):
        if self.user_ids:
            self.user_id = self.user_ids[0]
