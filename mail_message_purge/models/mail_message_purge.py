# Copyright 2024 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import logging

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.osv.expression import AND, OR
from odoo.tools import safe_eval

_logger = logging.getLogger(__name__)


class MailMessagePurge(models.Model):
    _name = "mail.message.purge"
    _description = "Mail Message Purge"

    def _get_default_mail_message_domain(self):
        selection_values = self.env["mail.message"]._fields["message_type"].selection
        domains = [[("message_type", "=", value[0])] for value in selection_values]
        return str(OR(domains))

    model_id = fields.Many2one(
        comodel_name="ir.model",
        domain=[("transient", "=", False), ("is_mail_thread", "=", True)],
        string="Target model",
        ondelete="cascade",
        required=True,
    )
    model_name = fields.Char(related="model_id.model", readonly=True)
    retention_period = fields.Integer(
        default=5, required=True, help="Retention period in years"
    )
    domain = fields.Char(string="Filtering domain")
    all_message_type = fields.Boolean(
        string="All message types",
        default=True,
        help="If unchecked a domain will allow to customize the message to be purged. "
        "Otherwise all message types will be included in the purge.",
    )
    mail_message_subtype_ids = fields.Many2many(
        comodel_name="mail.message.subtype",
        domain="['|', ('res_model', '=', model_name), ('res_model', '=', False)]",
        string="Subtypes",
    )
    mail_message_domain = fields.Char(
        string="Message filter", default=_get_default_mail_message_domain
    )
    active = fields.Boolean(default=True)

    def _domain_mail_message_purge(self):
        """Generate a domain to search for mail message to purge."""
        self.ensure_one()
        # __import__("pdb").set_trace()
        domain = [
            ("model", "=", self.model_id.model),
            (
                "create_date",
                "<",
                fields.Date.today() - relativedelta(years=self.retention_period),
            ),
        ]
        if not self.all_message_type:
            domain = AND([domain, safe_eval.safe_eval(self.mail_message_domain)])
        if self.mail_message_subtype_ids:
            domain = AND(
                [domain, [("subtype_id", "in", self.mail_message_subtype_ids.ids)]]
            )
        if self.domain:
            record_ids = (
                self.env[self.model_id.model]
                .search(safe_eval.safe_eval(self.domain))
                .ids
            )
            if record_ids:
                domain = AND([domain, [("res_id", "in", record_ids)]])
        return domain

    def _purge(self, limit=1000):
        domain = self._domain_mail_message_purge()
        messages = self.env["mail.message"].search(domain, limit=limit)
        _logger.info(f"Purging {len(messages)} messages for {self.model_id.model}")
        messages.unlink()

    @api.model
    def _cron_purge_mail_message(self, limit=1000):
        records = self.env["mail.message.purge"].search([])
        for record in records:
            record._purge(limit=limit)
