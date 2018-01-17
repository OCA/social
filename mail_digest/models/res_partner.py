# Copyright 2017-2018 Camptocamp - Simone Orsi
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import models, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # Shortcut to bypass this weird thing of odoo:
    # `partner.user_id` is the "saleman"
    # while the user is stored into `user_ids`
    # but in the majority of the cases we have one real user per partner.
    @property
    def real_user_id(self):
        return self.user_ids[0] if self.user_ids else False

    @api.multi
    def _notify(self, message,
                force_send=False, send_after_commit=True, user_signature=True):
        """Override to delegate domain generation."""
        # notify_by_email
        email_domain = self._get_notify_by_email_domain(message)
        # `sudo` from original odoo method
        # the reason should be that anybody can write messages to a partner
        # and you really want to find all ppl to be notified
        partners = self.sudo().search(email_domain)
        super(ResPartner, partners)._notify(
            message, force_send=force_send,
            send_after_commit=send_after_commit,
            user_signature=user_signature)
        # notify_by_digest
        digest_domain = self._get_notify_by_email_domain(message, digest=True)
        partners = self.sudo().search(digest_domain)
        partners._notify_by_digest(message)
        return True

    def _digest_enabled_message_types(self):
        """Return a list of enabled message types for digest.

        In `_notify_by_digest` we check if digest mode is enabled
        for given message's type. Here we retrieve global settings
        from a config param that you can customize to second your needs.
        """
        param = self.env['ir.config_parameter'].sudo().get_param(
            'mail_digest.enabled_message_types', default='')
        return [x.strip() for x in param.split(',') if x.strip()]

    @api.multi
    def _notify_by_digest(self, message):
        message_sudo = message.sudo()
        if message_sudo.message_type \
                not in self._digest_enabled_message_types():
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
            ('email', '!=', email),
            ('user_ids.digest_mode', '=', digest),
            ('user_ids.notification_type', '=', 'email'),
        ]
        if message.subtype_id:
            domain.extend(self._get_domain_subtype_leaf(message.subtype_id))
        return domain

    @api.model
    def _get_domain_subtype_leaf(self, subtype):
        return [
            '|',
            ('user_ids.disabled_notify_subtype_ids', 'not in', (subtype.id, )),
            ('user_ids.enabled_notify_subtype_ids', 'in', (subtype.id, )),
        ]
