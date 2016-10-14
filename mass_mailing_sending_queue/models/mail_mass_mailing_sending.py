# -*- coding: utf-8 -*-
# Copyright 2016 Antonio Espinosa <antonio.espinosa@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
from openerp import api, fields, models, tools

_logger = logging.getLogger(__name__)

BATCH_SIZE_DEFAULT = 500


class MailMassMailingSending(models.Model):
    _name = 'mail.mass_mailing.sending'

    state = fields.Selection([
        ('draft', "Draft"),
        ('enqueued', "Enqueued"),
        ('sending', "Sending"),
        ('sent', "Sent"),
        ('error', "Error"),
    ], string="State", required=True, copy=False, default='enqueued')
    mass_mailing_id = fields.Many2one(
        string="Mass mailing", comodel_name='mail.mass_mailing',
        readonly=True, ondelete='cascade')
    pending_count = fields.Integer(
        string="Pending recipients", compute='_compute_pending_count')
    sending_count = fields.Integer(
        string="Mails to be sent", compute='_compute_sending_count')
    sent_count = fields.Integer(
        string="Sent mails", compute='_compute_sent_count')
    failed_count = fields.Integer(
        string="Failed mails", compute='_compute_failed_count')
    error = fields.Char(string="Error message")
    date_start = fields.Datetime(
        string="Date start", default=fields.Datetime.now())
    date_end = fields.Datetime(string="Date end")

    @api.model
    def batch_size_get(self):
        m_param = self.env['ir.config_parameter']
        batch_size = BATCH_SIZE_DEFAULT
        batch_size_str = m_param.get_param(
            'mail.mass_mailing.sending.batch_size')
        if batch_size_str and batch_size_str.isdigit():
            batch_size = int(batch_size_str)
        return batch_size

    @api.multi
    def pending_emails(self):
        return self.env['mail.mail.statistics'].search([
            ('mass_mailing_sending_id', 'in', self.ids),
            ('scheduled', '!=', False),
            ('sent', '=', False),
            ('exception', '=', False),
        ])

    @api.multi
    def get_recipient_batch(self, res_ids):
        batch_size = self.batch_size_get()
        already_enqueued = self.env['mail.mail.statistics'].search([
            ('mass_mailing_sending_id', 'in', self.ids),
        ])
        set_ids = set(res_ids)
        new_ids = list(
            set_ids - set(already_enqueued.mapped('res_id')))
        if not self.env.context.get('sending_avoid_batch', False):
            new_ids = new_ids[:batch_size]
        if set(new_ids) != set_ids:
            return new_ids
        return res_ids

    @api.multi
    def pending_recipients(self):
        self.ensure_one()
        m_mailing = self.env['mail.mass_mailing'].with_context(
            mass_mailing_sending_id=self.id, sending_avoid_batch=True)
        return m_mailing.get_recipients(self.mass_mailing_id)

    @api.multi
    def send_mail(self):
        for sending in self:
            try:
                sending.with_context(mass_mailing_sending_id=sending.id).\
                    mass_mailing_id.send_mail()
            except Exception as e:
                sending._send_error(e)
        return True

    @api.multi
    def _send_error(self, exception):
        self.ensure_one()
        self.write({
            'error': tools.ustr(exception),
            'state': 'error',
            'date_end': fields.Datetime.now(),
        })
        self.mass_mailing_id.state = 'done'

    @api.multi
    def _process_enqueued(self):
        # Create mail_mail objects not created
        self.ensure_one()
        if self.pending_recipients():
            self.send_mail()
        # If there is no more recipient left, mark as sending
        if not self.pending_recipients():
            self.state = 'sending'
            self._process_sending()
        elif self.mass_mailing_id.state not in {'sending', 'error'}:
            self.mass_mailing_id.state = 'sending'

    @api.multi
    def _process_sending(self):
        # Check if there is any mail_mail object not sent
        self.ensure_one()
        if not self.pending_emails():
            self.mass_mailing_id.state = 'done'
            self.write({
                'state': 'sent',
                'date_end': fields.Datetime.now(),
            })
        elif self.mass_mailing_id.state not in {'sending', 'error'}:
            self.mass_mailing_id.state = 'sending'

    @api.multi
    def _process(self):
        self.ensure_one()
        method = getattr(self, '_process_%s' % self.state, None)
        if method and hasattr(method, '__call__'):
            return method()
        return False  # pragma: no cover

    @api.model
    def sendings_running(self):
        return self.search([
            ('state', 'in', ('enqueued', 'sending')),
        ])

    @api.model
    def cron(self):
        # Process all mail.mass_mailing.sending in enqueue or sending state
        sendings = self.sendings_running()
        for sending in sendings:
            _logger.info("Sending [%d] mass mailing [%d] '%s' (%s)",
                         sending.id, sending.mass_mailing_id.id,
                         sending.mass_mailing_id.name, sending.state)
            # Process sending using user who created it
            sending = sending.sudo(user=sending.create_uid.id)
            ctx = sending.create_uid.context_get()
            sending.with_context(**ctx)._process()
        return True

    @api.multi
    def _compute_pending_count(self):
        for sending in self.filtered(lambda r: r.state == 'enqueued'):
            sending.pending_count = len(sending.pending_recipients())

    @api.multi
    def _compute_sending_count(self):
        m_stats = self.env['mail.mail.statistics']
        for sending in self.filtered(
                lambda r: r.state in {'enqueued', 'sending'}):
            sending.sending_count = m_stats.search_count([
                ('mass_mailing_sending_id', '=', sending.id),
                ('scheduled', '!=', False),
                ('sent', '=', False),
                ('exception', '=', False),
            ])

    @api.multi
    def _compute_sent_count(self):
        m_stats = self.env['mail.mail.statistics']
        for sending in self:
            sending.sent_count = m_stats.search_count([
                ('mass_mailing_sending_id', '=', sending.id),
                ('scheduled', '!=', False),
                ('sent', '!=', False),
                ('exception', '=', False),
            ])

    @api.multi
    def _compute_failed_count(self):
        m_stats = self.env['mail.mail.statistics']
        for sending in self:
            sending.failed_count = m_stats.search_count([
                ('mass_mailing_sending_id', '=', sending.id),
                ('scheduled', '!=', False),
                ('exception', '!=', False),
            ])
