# Copyright 2021 Camptocamp (http://www.camptocamp.com).
# @author Iván Todorovich <ivan.todorovich@gmail.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class MailingList(models.Model):
    _inherit = "mailing.list"

    subscribe_template_id = fields.Many2one(
        "mail.template",
        string="Subscribe Notification",
        help="Leave empty to disable the email notification",
        domain=[("model", "=", "mailing.contact.subscription")],
        default=lambda self: self.env.ref(
            "mass_mailing_subscription_email.mailing_list_subscribe",
            raise_if_not_found=False,
        ),
    )
    unsubscribe_template_id = fields.Many2one(
        "mail.template",
        string="Unsubscribe Notification",
        help="Leave empty to disable the email notification",
        domain=[("model", "=", "mailing.contact.subscription")],
        default=lambda self: self.env.ref(
            "mass_mailing_subscription_email.mailing_list_unsubscribe",
            raise_if_not_found=False,
        ),
    )
