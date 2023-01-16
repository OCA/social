# Copyright 2023 Hunki Enterprises BV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools.safe_eval import _SAFE_OPCODES, test_expr


class MailActivityType(models.Model):
    _inherit = "mail.activity.type"

    field_ids = fields.Many2many(
        "ir.model.fields",
        domain="[('model_id', '=', res_model_id), ('ttype', '=', 'one2many')]",
    )
    code_activity_done = fields.Text(
        "Code done",
        help="Fill in code that is to be run when an activity of this type is set to done",
    )
    label_activity_done = fields.Char(
        "Label done button",
        help="Fill in the label of the 'Mark Done' button",
        translate=True,
    )
    code_user_selection = fields.Text(
        "Assign users from code",
        help="Fill in code that returns the users for which to create activities. "
        "This is useful in combination with the bulk assign wizard",
    )
    perm_read = fields.Boolean(
        "Bypass reading restrictions",
        help="A user assigned an activity of this type will always be able to access "
        "the underlying record, independent of other permissions",
    )
    perm_write = fields.Boolean(
        "Bypass writing restrictions",
        help="A user assigned an activity of this type will always be able to write on "
        "the underlying record, independent of other permissions",
    )

    @api.constrains("code_activity_done")
    def _check_code_activity_done(self):
        self._check_code("code_activity_done")

    @api.constrains("code_user_selection")
    def _check_code_user_selection(self):
        self._check_code("code_user_selection")

    def _check_code(self, field):
        for this in self:
            try:
                test_expr(this[field] or "True", _SAFE_OPCODES)
            except Exception as ex:
                raise UserError(
                    _("Failed to evaluate code: %s\n%s") % (this[field], str(ex))
                )

    @api.model_create_multi
    def create(self, vals_list):
        result = super().create(vals_list)
        self.clear_caches()
        return result

    def write(self, vals):
        result = super().write(vals)
        self.clear_caches()
        return result

    def unlink(self):
        result = super().unlink()
        self.clear_caches()
        return result
