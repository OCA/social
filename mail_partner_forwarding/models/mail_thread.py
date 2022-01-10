from odoo import models


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    def _notify_compute_recipients(self, message, msg_vals):
        """ Inherit this method to add in the list of partners to be notify
        the forwarding_partner_id of any partners in the list """
        recipient_data = super()._notify_compute_recipients(message, msg_vals)
        if not recipient_data.get("partners", False):
            return recipient_data
        partner_dict = {x.get("id"): x for x in recipient_data.get("partners")}
        forwarded_partner_ids = []
        # for each partner being notified we check if it has a
        # forwarding_partner_id configured that is not being notified yet
        for partner in (
            self.env["res.partner"]
            .sudo()
            .with_context(prefetch_fields=False)
            .browse(partner_dict.keys())
        ):
            if (
                partner.forwarding_partner_id
                and partner.forwarding_partner_id.id not in partner_dict.keys()
                and partner.forwarding_partner_id.id not in forwarded_partner_ids
            ):
                forwarded_partner_ids.append(partner.forwarding_partner_id.id)
                data = partner_dict[partner.id].copy()
                notif = (
                    partner.forwarding_partner_id.user_ids
                    and partner.forwarding_partner_id.user_ids[0].notification_type
                    or "email"
                )
                data.update(
                    {
                        "id": partner.forwarding_partner_id.id,
                        "share": partner.partner_share,
                        "notif": notif,
                    }
                )
                recipient_data["partners"].append(data)
        return recipient_data
