# Copyright 2016 Tecnativa - Antonio Espinosa
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class EventRegistrationState(models.Model):
    _name = "event.registration.state"
    _description = "Event Registration State"

    name = fields.Char(required=True)
    code = fields.Char(required=True)
