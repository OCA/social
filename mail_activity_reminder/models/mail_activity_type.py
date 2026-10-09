# Copyright 2020 Brainbean Apps (https://brainbeanapps.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from re import split

from odoo import fields, models


class MailActivityType(models.Model):
    _inherit = "mail.activity.type"

    reminders = fields.Char(
        help=(
            "A non-digit-separated list of offsets (in days) when reminders"
            ' should be fired: e.g. 0 means "on the deadline day" while'
            ' 5 means "5 calendar days before the deadline".'
        ),
    )
    reminder_mail_template_id = fields.Many2one(
        comodel_name="ir.ui.view",
        string="Reminder eMail Template",
        help="Optional reminder email template to use for this activity type",
    )

    def _get_reminder_offsets(self):
        """Hook for extensions"""
        self.ensure_one()
        if not self.reminders:
            return []
        return [int(x) for x in split(r"\D+", self.reminders) if x]
