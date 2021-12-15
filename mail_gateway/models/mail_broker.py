# Copyright 2020 Creu Blanca
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class MailBroker(models.Model):
    _name = "mail.broker"
    _description = "Mail Broker"

    name = fields.Char(required=True)
    token = fields.Char(required=True)
    _sql_constraints = [
        ("mail_broker_token", "unique(token)", "Token must be unique"),
    ]
    broker_type = fields.Selection([], required=True)
    show_on_app = fields.Boolean(default=True)
    webhook_url = fields.Char()
    webhook_user_id = fields.Many2one(
        "res.users", default=lambda self: self.env.user.id
    )

    @api.model
    def broker_fetch_slot(self):
        result = []
        for record in self.search([("show_on_app", "=", True)]):

            result.append(
                {
                    "id": record.id,
                    "name": record.name,
                    "channel_name": "broker_%s" % record.id,
                    "threads": [
                        thread._get_thread_data()
                        for thread in self.env["mail.broker.channel"].search(
                            [("show_on_app", "=", True), ("broker_id", "=", record.id)]
                        )
                    ],
                }
            )
        return result

    def channel_search(self, name):
        self.ensure_one()
        domain = [("broker_id", "=", self.id)]
        if name:
            domain += [("name", "ilike", "%" + name + "%")]
        return self.env["mail.broker.channel"].search(domain).read(["name"])
