# Copyright 2016 Tecnativa - Antonio Espinosa
# Copyright 2017 Tecnativa - Vicent Cubells
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class MailTrackingEmail(models.Model):
    _inherit = "mail.tracking.email"

    mass_mailing_id = fields.Many2one(
        string="Mass mailing", comodel_name="mailing.mailing", readonly=True
    )
    mail_stats_id = fields.Many2one(
        string="Mail statistics", comodel_name="mailing.trace", readonly=True
    )
    mail_id_int = fields.Integer(string="Mail ID", readonly=True)

    @api.model
    def _statistics_link_prepare(self, tracking):
        """Inherit this method to link other object to mailing.trace"""
        return {"mail_tracking_id": tracking.id}

    @api.depends("mail_stats_id")
    def _compute_message_id(self):
        """For the mass mailings, the message id is stored in the mailing.trace record."""
        res = super()._compute_message_id()
        for tracking in self.filtered("mail_stats_id"):
            tracking.message_id = tracking.mail_stats_id.message_id
        return res

    @api.model_create_multi
    def create(self, vals_list):
        tracking = super().create(vals_list)
        # Link mail statistics with this tracking
        if tracking.mail_stats_id:
            tracking.mail_stats_id.write(self._statistics_link_prepare(tracking))
        return tracking

    def _contacts_email_bounced_set(self, reason, event=None):
        recipients = []
        if event and event.recipient_address:
            recipients.append(event.recipient_address)
        else:
            recipients = list(filter(None, self.mapped("recipient_address")))
        for recipient in recipients:
            self.env["mailing.contact"].search(
                [("email", "=ilike", recipient)]
            ).email_bounced_set(self, reason, event=event)

    def smtp_error(self, mail_server, smtp_server, exception):
        res = super().smtp_error(mail_server, smtp_server, exception)
        self._contacts_email_bounced_set("error")
        return res

    def event_create(self, event_type, metadata):
        res = super().event_create(event_type, metadata)
        if event_type in {"hard_bounce", "spam", "reject"}:
            self._contacts_email_bounced_set(event_type)
        return res
