# Copyright 2016 ForgeFlow S.L.
# Copyright 2016 Serpent Consulting Services Pvt. Ltd.
# Copyright 2017 LasLabs Inc.
# Copyright 2018 Tecnativa - Vicent Cubells
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class MailMessage(models.Model):
    _inherit = "mail.message"

    subject = fields.Char(index="trigram")
    body = fields.Html(index="trigram")
    record_name = fields.Char(index="trigram")
    email_from = fields.Char(index="trigram")
    reply_to = fields.Char(index="trigram")
