# Copyright 2016 Antonio Espinosa - <antonio.espinosa@tecnativa.com>
# Copyright 2017 Vicent Cubells - <vicent.cubells@tecnativa.com>
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

    @api.model
    def create(self, vals):
        tracking = super(MailTrackingEmail, self).create(vals)
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
        res = super(MailTrackingEmail, self).smtp_error(
            mail_server, smtp_server, exception
        )
        self._contacts_email_bounced_set("error")
        return res

    def event_create(self, event_type, metadata):
        res = super(MailTrackingEmail, self).event_create(event_type, metadata)
        if event_type in {"hard_bounce", "spam", "reject"}:
            self._contacts_email_bounced_set(event_type)
        return res
