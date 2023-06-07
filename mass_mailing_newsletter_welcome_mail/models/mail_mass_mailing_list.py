# Copyright 2019 Tecnativa - Jairo Llopis
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class MailMassMailingList(models.Model):
    _inherit = 'mailing.list'

    welcome_mail_template_id = fields.Many2one(
        string="Welcome mail template",
        comodel_name='mail.template',
        ondelete='set null',
        help="Mail template to be sent when a contact is subscribed from "
             "the website."
    )
