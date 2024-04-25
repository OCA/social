from odoo import api, models


class MailMessage(models.Model):
    _inherit = "mail.message"

    @api.depends()
    def _compute_display_name(self):
        params = self.env.context.get("params")
        if params:
            model = params.get("model")
            view_type = params.get("view_type")
            if model == "mail.tracking.value" and view_type == "form":
                for rec in self:
                    if rec.display_name == "False":
                        rec.display_name = "Message ID - " + str(rec.id)
                    else:
                        rec.display_name = rec.display_name
