# Copyright 2016 Tecnativa - Antonio Espinosa
# Copyright 2017 Tecnativa - Vicent Cubells
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class MailTrace(models.Model):
    _inherit = "mailing.trace"

    mail_tracking_id = fields.Many2one(
        string="Mail tracking", comodel_name="mail.tracking.email", readonly=True
    )
    tracking_event_ids = fields.One2many(
        string="Tracking events",
        comodel_name="mail.tracking.event",
        related="mail_tracking_id.tracking_event_ids",
        readonly=True,
    )

    def write(self, values):
        """Ignore write from _postprocess_sent_message on selected ids"""
        to_ignore_ids = self.env.context.get("_ignore_write_trace_postprocess_ids")
        if to_ignore_ids:
            self = self.browse(set(self.ids) - set(to_ignore_ids))
        return super().write(values)
