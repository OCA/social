# Copyright 2024 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import logging

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.osv.expression import AND
from odoo.tools import safe_eval

_logger = logging.getLogger(__name__)


class MailMessagePurge(models.Model):
    _name = "mail.message.purge"
    _description = "Mail Message Purge"

    res_model = fields.Many2one(
        comodel_name="ir.model",
        domain=[("transient", "=", False), ("is_mail_thread", "=", True)],
        string="Target model",
        ondelete="cascade",
        required=True,
    )
    model_name = fields.Char(related="res_model.model", readonly=True)
    retention_period = fields.Integer(
        default=5, required=True, help="Retention period in years"
    )
    domain = fields.Char(string="Filtering domain")
    mail_message_subtype_ids = fields.Many2many(
        comodel_name="mail.message.subtype",
        domain="['|', ('res_model', '=', model_name), ('res_model', '=', False)]",
        string="Subtypes",
    )
    include_user_notification = fields.Boolean()
    active = fields.Boolean(default=True)

    def _domain_mail_message_purge(self):
        """Generate a domain to search for mail message to purge."""
        self.ensure_one()
        domain = [
            ("model", "=", self.res_model.model),
            (
                "create_date",
                "<",
                fields.Date.today() - relativedelta(years=self.retention_period),
            ),
        ]
        if self.include_user_notification:
            domain = AND(
                [
                    domain,
                    [("message_type", "in", ("notification", "user_notification"))],
                ]
            )
        else:
            domain = AND([domain, [("message_type", "=", "notification")]])
        if self.mail_message_subtype_ids:
            domain = AND(
                [domain, [("subtype_id", "in", self.mail_message_subtype_ids.ids)]]
            )
        if self.domain:
            record_ids = (
                self.env[self.res_model.model]
                .search(safe_eval.safe_eval(self.domain))
                .ids
            )
            if record_ids:
                domain = AND([domain, [("res_id", "in", record_ids)]])
        return domain

    def _purge(self):
        domain = self._domain_mail_message_purge()
        messages = self.env["mail.message"].search(domain, limit=1000)
        _logger.info(f"Purging {len(messages)} messages for {self.res_model.model}")
        messages.unlink()

    @api.model
    def _cron_purge_mail_message(self):
        records = self.env["mail.message.purge"].search([])
        for record in records:
            record._purge()
