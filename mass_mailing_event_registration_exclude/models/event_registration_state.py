# -*- coding: utf-8 -*-
# Copyright 2016 Antonio Espinosa <antonio.espinosa@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class EventRegistrationState(models.Model):
    _name = 'event.registration.state'

    name = fields.Char(required=True)
    code = fields.Char(required=True)
