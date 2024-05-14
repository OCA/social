# Copyright 2016 Antonio Espinosa - <antonio.espinosa@tecnativa.com>
# Copyright 2019 Alexandre Díaz
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from email.utils import getaddresses

from odoo import _, api, fields, models
from odoo.osv import expression
from odoo.tools import email_split


class MailMessage(models.Model):
    _inherit = "mail.message"

    # Recipients
    email_cc = fields.Char(
        "Cc", help="Additional recipients that receive a " '"Carbon Copy" of the e-mail'
    )
    email_to = fields.Char("To", help="Raw TO recipients")
    mail_tracking_ids = fields.One2many(
        comodel_name="mail.tracking.email",
        inverse_name="mail_message_id",
        auto_join=True,
        string="Mail Trackings",
    )
    mail_tracking_needs_action = fields.Boolean(
        help="The message tracking will be considered to filter tracking issues",
        default=False,
    )
    is_failed_message = fields.Boolean(
        compute="_compute_is_failed_message",
        search="_search_is_failed_message",
    )

    @api.model
    def get_failed_states(self):
        """The 'failed' states of the message"""
        return {"error", "rejected", "spam", "bounced", "soft-bounced"}

    @api.depends(
        "mail_tracking_needs_action",
        "author_id",
        "notification_ids",
        "mail_tracking_ids",
        "mail_tracking_ids.state",
    )
    def _compute_is_failed_message(self):
        """Compute 'is_failed_message' field for the active user"""
        failed_states = self.get_failed_states()
        for message in self:
            needs_action = message.mail_tracking_needs_action
            involves_me = self.env.user.partner_id in (
                message.author_id | message.notification_ids.res_partner_id
            )
            has_failed_trackings = failed_states.intersection(
                message.mapped("mail_tracking_ids.state")
            )
            message.is_failed_message = bool(
                needs_action and involves_me and has_failed_trackings
            )

    def _search_is_failed_message(self, operator, value):
        """Search for messages considered failed for the active user.
        Be notice that 'notificacion_ids' is a record that change if
        the user mark the message as readed.
        """
        # FIXME: Due to ORM issue with auto_join and 'OR' we construct the domain
        # using an extra query to get valid results.
        # For more information see: https://github.com/odoo/odoo/issues/25175
        notification_partner_ids = self.search(
            [("notification_ids.res_partner_id", "=", self.env.user.partner_id.id)]
        )
        return expression.normalize_domain(
            [
                (
                    "mail_tracking_ids.state",
                    "in" if value else "not in",
                    list(self.get_failed_states()),
                ),
                ("mail_tracking_needs_action", "=", True),
                "|",
                ("author_id", "=", self.env.user.partner_id.id),
                ("id", "in", notification_partner_ids.ids),
            ]
        )

    def _tracking_status_map_get(self):
        """Map tracking states to be used in chatter"""
        return {
            "False": "waiting",
            "error": "error",
            "deferred": "sent",
            "sent": "sent",
            "delivered": "delivered",
            "opened": "opened",
            "rejected": "error",
            "spam": "error",
            "unsub": "opened",
            "bounced": "error",
            "soft-bounced": "error",
        }

    def _partner_tracking_status_get(self, tracking_email):
        """Determine tracking status"""
        tracking_status_map = self._tracking_status_map_get()
        status = "unknown"
        if tracking_email:
            tracking_email_status = str(tracking_email.state)
            status = tracking_status_map.get(tracking_email_status, "unknown")
        return status

    def _partner_tracking_status_human_get(self, status):
        """Translations for tracking statuses to be used on qweb"""
        statuses = {
            "waiting": _("Waiting"),
            "error": _("Error"),
            "sent": _("Sent"),
            "delivered": _("Delivered"),
            "opened": _("Opened"),
            "unknown": _("Unknown"),
        }
        return _("Status: %s") % statuses[status]

    @api.model
    def _get_error_description(self, tracking):
        """Translations for error descriptions to be used on qweb"""
        descriptions = {"no_recipient": _("The partner doesn't have a defined email")}
        return descriptions.get(tracking.error_type, tracking.error_description)

    def tracking_status(self):
        """Generates a complete status tracking of the messages by partner"""
        self.ensure_one()
        tracking_delta = 0
        partner_trackings = []
        partners_already = self.env["res.partner"]
        partners = self.env["res.partner"]
        trackings = (
            self.env["mail.tracking.email"]
            .sudo()
            .search([("mail_message_id", "=", self.id)])
        )
        # String to List
        email_cc_list = self._drop_aliases(email_split(self.email_cc))
        email_to_list = self._drop_aliases(email_split(self.email_to))
        # Search related partners recipients
        partners |= partners.search([("email", "in", email_cc_list + email_to_list)])
        # Operate over set's instead of lists
        email_cc_list = set(email_cc_list)
        email_to_list = set(email_to_list) - email_cc_list
        # Search all trackings for this message
        for tracking in trackings:
            status = self._partner_tracking_status_get(tracking)
            recipient = tracking.partner_id.name or tracking.recipient
            partner_trackings.append(
                {
                    "status": status,
                    "status_human": self._partner_tracking_status_human_get(status),
                    "error_type": tracking.error_type,
                    "error_description": self._get_error_description(tracking),
                    "tracking_id": tracking.id,
                    "recipient": recipient,
                    "partner_id": tracking.partner_id.id,
                    "isCc": False,
                    "tracking_delta": "%i-%i" % (self.id, tracking_delta),
                }
            )
            if tracking.partner_id:
                # Discard mails with tracking
                email_cc_list.discard(tracking.partner_id.email)
                email_to_list.discard(tracking.partner_id.email)
                partners_already |= tracking.partner_id
            tracking_delta += 1
        # Search all partner recipients for this message
        if self.partner_ids:
            partners |= self.partner_ids
        if self.notified_partner_ids:
            partners |= self.notified_partner_ids
        # Discard partner recipients already included
        partners -= partners_already
        # Default tracking values
        tracking_unknown_values = {
            "status": "unknown",
            "status_human": self._partner_tracking_status_human_get("unknown"),
            "error_type": False,
            "error_description": False,
            "tracking_id": False,
        }
        # Process tracking status of partner recipients without tracking
        for partner in partners:
            # Discard 'To' with partner
            if partner.email in email_to_list:
                email_to_list.discard(partner.email)
            # If there is partners not included, then status is 'unknown'
            # and perhaps a Cc recipient
            isCc = False
            if partner.email in email_cc_list:
                email_cc_list.discard(partner.email)
                isCc = True
            tracking_status = tracking_unknown_values.copy()
            tracking_status.update(
                {
                    "recipient": partner.name,
                    "partner_id": partner.id,
                    "isCc": isCc,
                    "tracking_delta": "%i-%i" % (self.id, tracking_delta),
                }
            )
            partner_trackings.append(tracking_status)
            tracking_delta += 1
        # Process Cc/To recipients without partner
        for cc, lst in [(True, email_cc_list), (False, email_to_list)]:
            for email in lst:
                tracking_status = tracking_unknown_values.copy()
                tracking_status.update(
                    {
                        "recipient": email,
                        "partner_id": False,
                        "isCc": cc,
                        "tracking_delta": "%i-%i" % (self.id, tracking_delta),
                    }
                )
                partner_trackings.append(tracking_status)
                tracking_delta += 1
        return partner_trackings

    @api.model
    def _drop_aliases(self, mail_list):
        aliases = self.env["mail.alias"].get_aliases()

        def _filter_alias(email):
            email_wn = getaddresses([email])[0][1]
            if email_wn not in aliases:
                return email_wn

        return list(filter(_filter_alias, mail_list))

    def _prepare_dict_failed_message(self):
        """Preare values to be used by the chatter widget"""
        self.ensure_one()
        failed_trackings = self.mail_tracking_ids.filtered(
            lambda x: x.state in self.get_failed_states()
        )
        if not failed_trackings or not self.mail_tracking_needs_action:
            return
        failed_partners = failed_trackings.mapped("partner_id")
        failed_recipients = failed_partners.read(["display_name"])
        return {
            "id": self.id,
            "date": self.date,
            "body": self.body,
            "failed_recipients": failed_recipients,
        }

    def get_failed_messages(self):
        """Returns the list of failed messages to be used by the
        failed_messages widget"""
        return [
            msg._prepare_dict_failed_message()
            for msg in self.sorted("date", reverse=True)
        ]

    def set_need_action_done(self):
        """This will mark the messages to be ignored in the tracking issues filter"""
        self.check_access_rule("read")
        self.mail_tracking_needs_action = False
        self._notify_message_notification_update()

    @api.model
    def get_failed_count(self):
        """Gets the number of failed messages used on discuss mailbox item"""
        return self.search_count([("is_failed_message", "=", True)])

    @api.model
    def get_failed_messsage_info(self, ids, model):
        msg_ids = self.search([("res_id", "=", ids), ("model", "=", model)])
        res = [
            msg._prepare_dict_failed_message()
            for msg in msg_ids.sorted("date", reverse=True)
            if msg._prepare_dict_failed_message()
        ]
        return res

    def _message_notification_format(self):
        """Add info for the web client"""
        formatted_notifications = super()._message_notification_format()
        for notification in formatted_notifications:
            message = self.filtered(
                lambda x, notification=notification: x.id == notification["id"]
            )
            notification.update(
                {
                    "mail_tracking_needs_action": message.mail_tracking_needs_action,
                    "is_failed_message": message.is_failed_message,
                }
            )
        return formatted_notifications

    def _message_format_extras(self, format_reply):
        """Add info for the web client"""
        res = super()._message_format_extras(format_reply)
        res.update(
            {
                "partner_trackings": self.tracking_status(),
                "mail_tracking_needs_action": self.mail_tracking_needs_action,
                "is_failed_message": self.is_failed_message,
            }
        )
        return res
