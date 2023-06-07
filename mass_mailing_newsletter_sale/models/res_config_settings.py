from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    sale_mailing_list_id = fields.Many2one(
        comodel_name="mailing.list", string="Mailing list"
    )

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        IrDefault = self.env["ir.default"].sudo()
        IrDefault.set(
            "res.config.settings", "sale_mailing_list_id", self.sale_mailing_list_id.id
        )
        return True

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        IrDefault = self.env["ir.default"].sudo()
        res.update(
            {
                "sale_mailing_list_id": IrDefault.get(
                    "res.config.settings", "sale_mailing_list_id"
                ),
            }
        )
        return res
