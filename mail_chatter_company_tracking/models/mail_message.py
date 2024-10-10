from odoo import models


class Message(models.Model):
    _inherit = "mail.message"

    def _message_format(self, fnames):
        vals_list = super()._message_format(fnames)
        for pos, vals in enumerate(vals_list):
            tracking_ids = map(lambda x: x.get("id"), vals["tracking_value_ids"])
            trackings = self.env["mail.tracking.value"].browse(tracking_ids)
            tracking_value_ids = []
            for tracking in trackings:
                tracking_value_ids.append(
                    {
                        "id": tracking.id,
                        "changed_field": tracking.field_desc,
                        "old_value": tracking.get_old_display_value()[0],
                        "new_value": tracking.get_new_display_value()[0],
                        "field_type": tracking.field_type,
                        "company_name": (
                            tracking.company_id.name
                            if self.env[tracking.field.model]
                            ._fields[tracking.field.name]
                            .company_dependent
                            else False
                        ),
                    }
                )
            vals_list[pos]["tracking_value_ids"] = tracking_value_ids
        return vals_list
