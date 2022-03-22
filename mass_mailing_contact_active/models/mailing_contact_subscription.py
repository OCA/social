# Copyright 2022 Camptocamp SA
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl)
from odoo import fields, models


class MailingContactSubscription(models.Model):

    _inherit = "mailing.contact.subscription"

    active = fields.Boolean(default=True)
