# Copyright 2022 Hunki Enterprises BV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import api, fields, models
from odoo.tools.safe_eval import safe_eval


class MailActivity(models.Model):
    _inherit = "mail.activity"

    equivalent_activity_ids = fields.Many2many(
        "mail.activity", "mail_activity_equivalent_rel", "this_id", "other_id",
    )
    label_activity_done = fields.Char(
        related=("activity_type_id", "label_activity_done")
    )

    @api.model
    def _setup_base(self):
        """Disable the field for models that aren't mail.activity, as many2many
        fields cause problems with inheritance by delegation"""
        if self._name != "mail.activity":
            self.__class__.equivalent_activity_ids = None
        super()._setup_base()

    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        """Disable active_test when we search for permission activities"""
        if len(args) == 1 and args[0][0].startswith("activity_type_id.perm_"):
            self = self.with_context(active_test=False)
        return super().search(
            args, offset=offset, limit=limit, order=order, count=count
        )

    @api.model
    def _activity_access_eval(self, code, res_model, res_id):
        eval_context = (
            self.env["ir.actions.server"]
            .with_context(
                active_id=res_id, active_ids=[res_id], active_model=res_model,
            )
            ._get_eval_context(
                action=self.env["ir.actions.server"].new(
                    {
                        "model_id": self.env["ir.model"]._get_id(res_model),
                        "model_name": res_model,
                    }
                )
            )
        )
        return safe_eval(code, eval_context)

    def _action_done(self, feedback=False, attachment_ids=None):
        activity_done = [
            (this.res_model, this.res_id, this.activity_type_id.code_activity_done)
            for this in self
            if this.activity_type_id.code_activity_done
        ]
        result = super()._action_done(feedback=feedback, attachment_ids=attachment_ids)
        self.sudo().mapped("equivalent_activity_ids").write(
            {"done": True, "active": False, "date_done": fields.Date.today()}
        )
        for res_model, res_id, code in activity_done:
            self._activity_access_eval(code, res_model, res_id)
        return result
