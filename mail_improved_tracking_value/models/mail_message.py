from odoo import api, models


class MailMessage(models.Model):
    _inherit = "mail.message"

    @api.model
    def name_get(self):
        res = super(MailMessage, self).name_get()
        params = self.env.context.get("params")
        if params:
            model = params.get("model")
            view_type = params.get("view_type")
            if model == "mail.tracking.value" and view_type == "form":
                for rec in res:
                    if rec[1] == "False":
                        new_name = (rec[0], "Message ID - " + str(rec[0]))
                        res[res.index(rec)] = new_name
        return res
