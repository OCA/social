# Copyright 2017-2018 Camptocamp - Simone Orsi
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import models, fields, api


class Users(models.Model):
    _name = 'res.users'
    _inherit = ['res.users']

    def __init__(self, pool, cr):
        """ Override of __init__ to add access rights.

        Access rights are disabled by default, but allowed
        on some specific fields defined in self.SELF_{READ/WRITE}ABLE_FIELDS.

        [copied from mail.models.users]
        """
        super(Users, self).__init__(pool, cr)
        new_fields = [
            'digest_mode',
            'digest_frequency',
            'notify_conf_ids',
        ]
        # duplicate list to avoid modifying the original reference
        type(self).SELF_WRITEABLE_FIELDS = list(self.SELF_WRITEABLE_FIELDS)
        type(self).SELF_WRITEABLE_FIELDS.extend(new_fields)
        # duplicate list to avoid modifying the original reference
        type(self).SELF_READABLE_FIELDS = list(self.SELF_READABLE_FIELDS)
        type(self).SELF_READABLE_FIELDS.extend(new_fields)

    digest_mode = fields.Boolean(
        default=False,
        help='If enabled, email notifications will be sent in digest mode.'
    )
    digest_frequency = fields.Selection(
        string='Frequency',
        selection=[
            ('daily', 'Daily'),
            ('weekly', 'Weekly')
        ],
        default='weekly',
        required=True,
    )
    notify_conf_ids = fields.One2many(
        string='Notifications',
        inverse_name='user_id',
        comodel_name='user.notification.conf',
    )
    enabled_notify_subtype_ids = fields.Many2many(
        string='User enabled subtypes',
        comodel_name='mail.message.subtype',
        compute='_compute_notify_subtype_ids',
        search='_search_enabled_notify_subtype_ids',
    )
    disabled_notify_subtype_ids = fields.Many2many(
        string='User disabled subtypes',
        comodel_name='mail.message.subtype',
        compute='_compute_notify_subtype_ids',
        search='_search_disabled_notify_subtype_ids',
    )

    def _notify_subtypes_by_state(self, enabled):
        self.ensure_one()
        return self.notify_conf_ids.filtered(
            lambda x: x.enabled == enabled).mapped('subtype_id')

    @api.multi
    @api.depends('notify_conf_ids.subtype_id', 'notify_conf_ids.enabled')
    def _compute_notify_subtype_ids(self):
        for rec in self:
            rec.enabled_notify_subtype_ids = \
                rec._notify_subtypes_by_state(True)
            rec.disabled_notify_subtype_ids = \
                rec._notify_subtypes_by_state(False)

    def _search_notify_subtype_ids_domain(self, operator, value, enabled):
        """Build domain to search notification subtypes by user conf."""
        if operator in ('in', 'not in') and \
                not isinstance(value, (tuple, list)):
            value = [value, ]
        conf_value = value
        if isinstance(conf_value, int):
            # we search conf records always w/ 'in'
            conf_value = [conf_value]
        _value = self.env['user.notification.conf'].search([
            ('subtype_id', 'in', conf_value),
            ('enabled', '=', enabled),
        ]).mapped('user_id').ids
        return [('id', operator, _value)]

    def _search_enabled_notify_subtype_ids(self, operator, value):
        return self._search_notify_subtype_ids_domain(operator, value, True)

    def _search_disabled_notify_subtype_ids(self, operator, value):
        return self._search_notify_subtype_ids_domain(operator, value, False)

    def _notify_update_subtype(self, subtype, enable):
        """Update notification settings by subtype.

        :param subtype: `mail.message.subtype` to enable or disable
        :param enable: boolean to enable or disable given subtype
        """
        self.ensure_one()
        exists = self.env['user.notification.conf'].search([
            ('subtype_id', '=', subtype.id),
            ('user_id', '=', self.id)
        ], limit=1)
        if exists:
            exists.enabled = enable
        else:
            self.write({
                'notify_conf_ids': [
                    (0, 0, {'enabled': enable, 'subtype_id': subtype.id})]
            })

    @api.multi
    def _notify_enable_subtype(self, subtype):
        """Enable given subtype."""
        for rec in self:
            rec._notify_update_subtype(subtype, True)

    @api.multi
    def _notify_disable_subtype(self, subtype):
        """Disable given subtype."""
        for rec in self:
            rec._notify_update_subtype(subtype, False)
