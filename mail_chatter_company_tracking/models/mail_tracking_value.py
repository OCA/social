from odoo import api, fields, models


class MailTrackingValue(models.Model):
    _inherit = "mail.tracking.value"

    company_id = fields.Many2one(
        "res.company",
        default=lambda self: self.env.company,
    )

    @api.model
    def create_tracking_values(
        self,
        initial_value,
        new_value,
        col_name,
        col_info,
        tracking_sequence,
        model_name,
    ):
        res = super().create_tracking_values(
            initial_value, new_value, col_name, col_info, tracking_sequence, model_name
        )
        if res:
            res.update(
                {
                    "company_id": self.env.company.id,
                }
            )
        return res
