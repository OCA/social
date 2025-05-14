# Copyright 2015 Therp BV <http://therp.nl>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import fields, models


class MailFollowers(models.Model):
    _inherit = "mail.followers"

    mail_follower_custom_notification = fields.Json()

    def _get_recipient_data(self, records, message_type, subtype_id, pids=None):
        result = super()._get_recipient_data(
            records, message_type, subtype_id, pids=pids
        )
        if subtype_id:
            subtype = self.env["mail.message.subtype"].browse(subtype_id)
            subtype_notification_type = subtype.mail_follower_custom_notification
            if subtype_notification_type and (
                not subtype.mail_follower_custom_notification_model_ids
                or records
                and records._name
                in subtype.mail_follower_custom_notification_model_ids.mapped("model")
            ):
                for followers in result.values():
                    for follower_data in followers.values():
                        follower_data["notif"] = subtype_notification_type
        if records and subtype_id:
            for record in records:
                for follower in record.message_follower_ids:
                    if not follower.mail_follower_custom_notification:
                        continue
                    custom_notification = (
                        follower.mail_follower_custom_notification.get(str(subtype_id))
                    )
                    if custom_notification:
                        result[record.id][follower.partner_id.id][
                            "notif"
                        ] = custom_notification
        return result
