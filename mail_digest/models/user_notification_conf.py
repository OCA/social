# Copyright 2017-2018 Camptocamp - Simone Orsi
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import models, fields


class UserNotificationConf(models.Model):
    """Hold user's single notification configuration."""
    _name = 'user.notification.conf'
    _description = 'User notification configuration'
    # TODO: add friendly onchange to not yield errors when editin via UI
    _sql_constraints = [
        ('unique_user_subtype_conf',
         'unique (user_id,subtype_id)',
         'You can have only one configuration per subtype!')
    ]

    user_id = fields.Many2one(
        string='User',
        comodel_name='res.users',
        readonly=True,
        required=True,
        ondelete='cascade',
        index=True,
    )
    subtype_id = fields.Many2one(
        'mail.message.subtype',
        'Notification type',
        ondelete='cascade',
        required=True,
        index=True,
    )
    enabled = fields.Boolean(default=True, index=True)
