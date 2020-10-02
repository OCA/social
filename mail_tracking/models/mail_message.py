# Copyright 2016 Antonio Espinosa - <antonio.espinosa@tecnativa.com>
# Copyright 2019 Alexandre Díaz
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import _, models, api, fields
from email.utils import getaddresses
from odoo.tools import email_split
from odoo.osv import expression


class MailMessage(models.Model):
    _inherit = "mail.message"

    # Recipients
    email_cc = fields.Char("Cc", help='Additional recipients that receive a '
                                      '"Carbon Copy" of the e-mail')
    email_to = fields.Char("To", help='Raw TO recipients')
    mail_tracking_ids = fields.One2many(
        comodel_name='mail.tracking.email',
        inverse_name='mail_message_id',
        string="Mail Trackings",
        auto_join=True,
    )
    mail_tracking_needs_action = fields.Boolean(
        help="The message tracking will be considered"
             " to filter tracking issues",
        default=False,
    )
    is_failed_message = fields.Boolean(
        compute="_compute_is_failed_message",
        search='_search_is_failed_message',
    )

    @api.model
    def get_failed_states(self):
        """The 'failed' states of the message"""
        return {'error', 'rejected', 'spam', 'bounced', 'soft-bounced'}

    @api.depends('mail_tracking_needs_action', 'author_id', 'notification_ids',
                 'mail_tracking_ids.state')
    def _compute_is_failed_message(self):
        """Compute 'is_failed_message' field for the active user"""
        failed_states = self.get_failed_states()
        for message in self:
            needs_action = message.mail_tracking_needs_action
            involves_me = self.env.user.partner_id in (
                message.author_id | message.notification_ids.mapped('res_partner_id'))
            has_failed_trackings = failed_states.intersection(
                message.mapped("mail_tracking_ids.state"))
            message.is_failed_message = bool(
                needs_action and involves_me and has_failed_trackings)

    def _search_is_failed_message(self, operator, value):
        """Search for messages considered failed for the active user.
        Be notice that 'notificacion_ids' is a record that change if
        the user mark the message as readed.
        """
        # FIXME: Due to ORM issue with auto_join and 'OR' we construct the domain
        # using an extra query to get valid results.
        # For more information see: https://github.com/odoo/odoo/issues/25175
        notification_partner_ids = self.search([
            ('notification_ids.res_partner_id', '=', self.env.user.partner_id.id)
        ])
        return expression.normalize_domain([
            (
                'mail_tracking_ids.state',
                'in' if value else 'not in',
                list(self.get_failed_states())
            ),
            ('mail_tracking_needs_action', '=', True),
            '|',
            ('author_id', '=', self.env.user.partner_id.id),
            ('id', 'in', notification_partner_ids.ids),
        ])

    def _tracking_status_map_get(self):
        """Map tracking states to be used in chatter"""
        return {
            'False': 'waiting',
            'error': 'error',
            'deferred': 'sent',
            'sent': 'sent',
            'delivered': 'delivered',
            'opened': 'opened',
            'rejected': 'error',
            'spam': 'error',
            'unsub': 'opened',
            'bounced': 'error',
            'soft-bounced': 'error',
        }

    def _partner_tracking_status_get(self, tracking_email):
        """Determine tracking status"""
        tracking_status_map = self._tracking_status_map_get()
        status = 'unknown'
        if tracking_email:
            tracking_email_status = str(tracking_email.state)
            status = tracking_status_map.get(tracking_email_status, 'unknown')
        return status

    def _partner_tracking_status_human_get(self, status):
        """Translations for tracking statuses to be used on qweb"""
        statuses = {'waiting': _('Waiting'), 'error': _('Error'),
                    'sent': _('Sent'), 'delivered': _('Delivered'),
                    'opened': _('Opened'), 'unknown': _('Unknown')}
        return _("Status: %s") % statuses[status]

    @api.model
    def _get_error_description(self, tracking):
        """Translations for error descriptions to be used on qweb"""
        descriptions = {
            'no_recipient': _("The partner doesn't have a defined email"),
        }
        return descriptions.get(tracking.error_type,
                                tracking.error_description)

    def tracking_status(self):
        """Generates a complete status tracking of the messages by partner"""
        res = {}
        for message in self:
            partner_trackings = []
            partners_already = self.env['res.partner']
            partners = self.env['res.partner']
            trackings = self.env['mail.tracking.email'].sudo().search([
                ('mail_message_id', '=', message.id),
            ])
            # String to List
            email_cc_list = self._drop_aliases(email_split(message.email_cc))
            email_to_list = self._drop_aliases(email_split(message.email_to))
            # Search related partners recipients
            partners |= partners.search([
                ('email', 'in', email_cc_list + email_to_list),
            ])
            # Operate over set's instead of lists
            email_cc_list = set(email_cc_list)
            email_to_list = set(email_to_list) - email_cc_list
            # Search all trackings for this message
            for tracking in trackings:
                status = self._partner_tracking_status_get(tracking)
                recipient = (
                    tracking.partner_id.name or tracking.recipient)
                partner_trackings.append({
                    'status': status,
                    'status_human':
                        self._partner_tracking_status_human_get(status),
                    'error_type': tracking.error_type,
                    'error_description':
                        self._get_error_description(tracking),
                    'tracking_id': tracking.id,
                    'recipient': recipient,
                    'partner_id': tracking.partner_id.id,
                    'isCc': False,
                })
                if tracking.partner_id:
                    # Discard mails with tracking
                    email_cc_list.discard(tracking.partner_id.email)
                    email_to_list.discard(tracking.partner_id.email)
                    partners_already |= tracking.partner_id
            # Search all partner recipients for this message
            if message.partner_ids:
                partners |= message.partner_ids
            if message.needaction_partner_ids:
                partners |= message.needaction_partner_ids
            # Discard partner recipients already included
            partners -= partners_already
            # Default tracking values
            tracking_unknown_values = {
                'status': 'unknown',
                'status_human':  self._partner_tracking_status_human_get(
                    'unknown'),
                'error_type': False,
                'error_description': False,
                'tracking_id': False,
            }
            # Process tracking status of partner recipients without tracking
            for partner in partners:
                # Discard 'To' with partner
                if partner.email in email_to_list:
                    email_to_list.discard(partner.email)
                # If there is partners not included, then status is 'unknown'
                # and perhaps a Cc recipient
                isCc = False
                if partner.email in email_cc_list:
                    email_cc_list.discard(partner.email)
                    isCc = True
                tracking_status = tracking_unknown_values.copy()
                tracking_status.update({
                    'recipient': partner.name,
                    'partner_id': partner.id,
                    'isCc': isCc,
                })
                partner_trackings.append(tracking_status)
            # Process Cc/To recipients without partner
            for cc, lst in [(True, email_cc_list), (False, email_to_list)]:
                for email in lst:
                    tracking_status = tracking_unknown_values.copy()
                    tracking_status.update({
                        'recipient': email,
                        'partner_id': False,
                        'isCc': cc,
                    })
                    partner_trackings.append(tracking_status)
            res[message.id] = {
                'partner_trackings': partner_trackings,
                'is_failed_message': message.is_failed_message,
            }
        return res

    @api.model
    def _drop_aliases(self, mail_list):
        aliases = self.env['mail.alias'].get_aliases()

        def _filter_alias(email):
            email_wn = getaddresses([email])[0][1]
            if email_wn not in aliases:
                return email_wn
        return list(filter(_filter_alias, mail_list))

    @api.model
    def _message_read_dict_postprocess(self, messages, message_tree):
        """Preare values to be used by the chatter widget"""
        res = super()._message_read_dict_postprocess(
            messages, message_tree)
        mail_message_ids = {m.get('id') for m in messages if m.get('id')}
        mail_messages = self.browse(mail_message_ids)
        tracking_statuses = mail_messages.tracking_status()
        for message_dict in messages:
            mail_message_id = message_dict.get('id', False)
            if mail_message_id:
                message_dict.update(tracking_statuses[mail_message_id])
        return res

    @api.multi
    def _prepare_dict_failed_message(self):
        """Preare values to be used by the chatter widget"""
        self.ensure_one()
        failed_trackings = self.mail_tracking_ids.filtered(
            lambda x: x.state in self.get_failed_states())
        failed_partners = failed_trackings.mapped('partner_id')
        failed_recipients = failed_partners.name_get()
        if self.author_id:
            author = self.author_id.name_get()[0]
        else:
            author = (-1, _('-Unknown Author-'))
        return {
            'id': self.id,
            'date': self.date,
            'author': author,
            'body': self.body,
            'failed_recipients': failed_recipients,
        }

    @api.multi
    def get_failed_messages(self):
        """Returns the list of failed messages to be used by the
           failed_messages widget"""
        return [msg._prepare_dict_failed_message()
                for msg in self.sorted('date', reverse=True)]

    @api.multi
    def set_need_action_done(self):
        """Set message tracking action as done

        This will mark them to be ignored in the tracking issues filter.
        """
        self.check_access_rule('read')
        self.write({'mail_tracking_needs_action': False})
        notification = {
            'type': 'toggle_tracking_status',
            'message_ids': self.ids,
            'needs_actions': False
        }
        self.env['bus.bus'].sendone(
            (self._cr.dbname, 'res.partner', self.env.user.partner_id.id),
            notification)

    @api.model
    def get_failed_count(self):
        """ Gets the number of failed messages used on discuss mailbox item"""
        return self.search_count([("is_failed_message", "=", True)])

    @api.model
    def set_all_as_reviewed(self):
        """ Sets all messages in the given domain as reviewed.

        Used by Discuss """

        unreviewed_messages = self.search([("is_failed_message", "=", True)])
        unreviewed_messages.write({'mail_tracking_needs_action': False})
        ids = unreviewed_messages.ids

        self.env['bus.bus'].sendone(
            (self._cr.dbname, 'res.partner',
             self.env.user.partner_id.id),
            {
                'type': 'toggle_tracking_status',
                'message_ids': ids,
                'needs_actions': False,
            }
        )

        return ids
