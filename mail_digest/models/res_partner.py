# -*- coding: utf-8 -*-
# Copyright 2017 Simone Orsi <simone.orsi@camptocamp.com>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from openerp import models, fields, api, _


class ResPartner(models.Model):
    _inherit = 'res.partner'

    notify_email = fields.Selection(selection_add=[('digest', _('Digest'))])
    notify_frequency = fields.Selection(
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
        inverse_name='partner_id',
        comodel_name='partner.notification.conf',
    )
    enabled_notify_subtype_ids = fields.Many2many(
        string='Partner enabled subtypes',
        comodel_name='mail.message.subtype',
        compute='_compute_enabled_notify_subtype_ids',
        search='_search_enabled_notify_subtype_ids',
    )
    disabled_notify_subtype_ids = fields.Many2many(
        string='Partner disabled subtypes',
        comodel_name='mail.message.subtype',
        compute='_compute_disabled_notify_subtype_ids',
        search='_search_disabled_notify_subtype_ids',
    )

    @api.multi
    def _compute_notify_subtypes(self, enabled):
        self.ensure_one()
        query = (
            'SELECT subtype_id FROM partner_notification_conf '
            'WHERE partner_id=%s AND enabled = %s'
        )
        self.env.cr.execute(
            query, (self.id, enabled))
        return [x[0] for x in self.env.cr.fetchall()]

    @api.multi
    @api.depends('notify_conf_ids.subtype_id')
    def _compute_enabled_notify_subtype_ids(self):
        for partner in self:
            partner.enabled_notify_subtype_ids = \
                partner._compute_notify_subtypes(True)

    @api.multi
    @api.depends('notify_conf_ids.subtype_id')
    def _compute_disabled_notify_subtype_ids(self):
        for partner in self:
            partner.disabled_notify_subtype_ids = \
                partner._compute_notify_subtypes(False)

    def _search_notify_subtype_ids_domain(self, operator, value, enabled):
        if operator in ('in', 'not in') and \
                not isinstance(value, (tuple, list)):
            value = [value, ]
        conf_value = value
        if isinstance(conf_value, int):
            # we search conf records always w/ 'in'
            conf_value = [conf_value]
        _value = self.env['partner.notification.conf'].search([
            ('subtype_id', 'in', conf_value),
            ('enabled', '=', enabled),
        ]).mapped('partner_id').ids
        return [('id', operator, _value)]

    def _search_enabled_notify_subtype_ids(self, operator, value):
        return self._search_notify_subtype_ids_domain(
            operator, value, True)

    def _search_disabled_notify_subtype_ids(self, operator, value):
        return self._search_notify_subtype_ids_domain(
            operator, value, False)

    @api.multi
    def _notify(self, message, force_send=False, user_signature=True):
        """Override to delegate domain generation."""
        # notify_by_email
        email_domain = self._get_notify_by_email_domain(message)
        # `sudo` from original odoo method
        # the reason should be that anybody can write messages to a partner
        # and you really want to find all ppl to be notified
        partners = self.sudo().search(email_domain)
        partners._notify_by_email(
            message, force_send=force_send, user_signature=user_signature)
        # notify_by_digest
        digest_domain = self._get_notify_by_email_domain(
            message, digest=True)
        partners = self.sudo().search(digest_domain)
        partners._notify_by_digest(message)

        # notify_by_chat
        self._notify_by_chat(message)
        return True

    @api.multi
    def _notify_by_digest(self, message):
        message_sudo = message.sudo()
        if not message_sudo.message_type == 'email':
            return
        self.env['mail.digest'].sudo().create_or_update(self, message)

    @api.model
    def _get_notify_by_email_domain(self, message, digest=False):
        """Return domain to collect partners to be notified by email.

        :param message: instance of mail.message
        :param digest: include/exclude digest enabled partners

        NOTE: since mail.mail inherits from mail.message
        this method is called even when
        we create the final email for mail.digest object.
        Here we introduce a new context flag `notify_only_recipients`
        to explicitely retrieve only partners among message's recipients.
        """

        message_sudo = message.sudo()
        channels = message.channel_ids.filtered(
            lambda channel: channel.email_send)
        email = message_sudo.author_id \
            and message_sudo.author_id.email or message.email_from

        ids = self.ids
        if self.env.context.get('notify_only_recipients'):
            ids = [x for x in ids if x in message.partner_ids.ids]
        domain = [
            '|',
            ('id', 'in', ids),
            ('channel_ids', 'in', channels.ids),
            ('email', '!=', email)
        ]
        if not digest:
            domain.append(('notify_email', 'not in', ('none', 'digest')))
        else:
            domain.append(('notify_email', '=', 'digest'))
        if message.subtype_id:
            domain.extend(self._get_domain_subtype_leaf(message.subtype_id))
        return domain

    @api.model
    def _get_domain_subtype_leaf(self, subtype):
        return [
            '|',
            ('disabled_notify_subtype_ids', 'not in', (subtype.id, )),
            ('enabled_notify_subtype_ids', 'in', (subtype.id, )),
        ]

    @api.multi
    def _notify_update_subtype(self, subtype, enable):
        self.ensure_one()
        exists = self.env['partner.notification.conf'].search([
            ('subtype_id', '=', subtype.id),
            ('partner_id', '=', self.id)
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
        self._notify_update_subtype(subtype, True)

    @api.multi
    def _notify_disable_subtype(self, subtype):
        self._notify_update_subtype(subtype, False)


class PartnerNotificationConf(models.Model):
    """Hold partner's single notification configuration."""
    _name = 'partner.notification.conf'
    _description = 'Partner notification configuration'
    # TODO: add friendly onchange to not yield errors when editin via UI
    _sql_constraints = [
        ('unique_partner_subtype_conf',
         'unique (partner_id,subtype_id)',
         'You can have only one configuration per subtype!')
    ]

    partner_id = fields.Many2one(
        string='Partner',
        comodel_name='res.partner',
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
    )
    enabled = fields.Boolean(default=True, index=True)
