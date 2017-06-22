# -*- coding: utf-8 -*-
# Copyright 2016 Antonio Espinosa - <antonio.espinosa@tecnativa.com>
# Copyright 2017 Vicent Cubells - <vicent.cubells@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models, fields


class MailMailStatistics(models.Model):
    _inherit = "mail.mail.statistics"

    mail_tracking_id = fields.Many2one(
        string="Mail tracking", comodel_name='mail.tracking.email',
        readonly=True)
    tracking_event_ids = fields.One2many(
        string="Tracking events", comodel_name='mail.tracking.event',
        related='mail_tracking_id.tracking_event_ids', readonly=True)
