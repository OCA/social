# -*- coding: utf-8 -*-
# Copyright 2017 Simone Orsi <simone.orsi@camptocamp.com>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from openerp import fields, models, api, _

import logging

logger = logging.getLogger('[mail_digest]')


class MailDigest(models.Model):
    _name = 'mail.digest'
    _description = 'Mail digest'
    _order = 'create_date desc'

    name = fields.Char(
        string="Name",
        compute="_compute_name",
        readonly=True,
    )
    # maybe we can retrieve the from messages?
    partner_id = fields.Many2one(
        string='Partner',
        comodel_name='res.partner',
        readonly=True,
        required=True,
        ondelete='cascade',
    )
    frequency = fields.Selection(
        related='partner_id.notify_frequency',
        readonly=True,
    )
    message_ids = fields.Many2many(
        comodel_name='mail.message',
        string='Messages'
    )
    # TODO: take care of `auto_delete` feature
    mail_id = fields.Many2one(
        'mail.mail',
        'Mail',
        ondelete='set null',
    )
    state = fields.Selection(related='mail_id.state')

    @api.multi
    @api.depends("partner_id", "partner_id.notify_frequency")
    def _compute_name(self):
        for rec in self:
            rec.name = u'{} - {}'.format(
                rec.partner_id.name, rec._get_subject())

    @api.model
    def create_or_update(self, partners, message, subtype_id=None):
        subtype_id = subtype_id or message.subtype_id
        for partner in partners:
            digest = self._get_or_create_by_partner(partner, message)
            digest.message_ids |= message
        return True

    @api.model
    def _get_by_partner(self, partner, mail_id=False):
        domain = [
            ('partner_id', '=', partner.id),
            ('mail_id', '=', mail_id),
        ]
        return self.search(domain, limit=1)

    @api.model
    def _get_or_create_by_partner(self, partner, message=None, mail_id=False):
        existing = self._get_by_partner(partner, mail_id=mail_id)
        if existing:
            return existing
        values = {'partner_id': partner.id, }
        return self.create(values)

    @api.model
    def _message_group_by_key(self, msg):
        return msg.subtype_id.id

    @api.multi
    def _message_group_by(self):
        self.ensure_one()
        grouped = {}
        for msg in self.message_ids:
            grouped.setdefault(self._message_group_by_key(msg), []).append(msg)
        return grouped

    def _get_template(self):
        # TODO: move this to a configurable field
        return self.env.ref('mail_digest.default_digest_tmpl')

    def _get_site_name(self):
        # default to company
        name = self.env.user.company_id.name
        if 'website' in self.env:
            try:
                ws = self.env['website'].get_current_website()
            except RuntimeError:
                # RuntimeError: object unbound -> no website request
                ws = None
            if ws:
                name = ws.name
        return name

    @api.multi
    def _get_subject(self):
        # TODO: shall we move this to computed field?
        self.ensure_one()
        subject = self._get_site_name() + ' '
        if self.partner_id.notify_frequency == 'daily':
            subject += _('Daily update')
        elif self.partner_id.notify_frequency == 'weekly':
            subject += _('Weekly update')
        return subject

    @api.multi
    def _get_template_values(self):
        self.ensure_one()
        subject = self._get_subject()
        template_values = {
            'digest': self,
            'subject': subject,
            'grouped_messages': self._message_group_by(),
            'base_url':
                self.env['ir.config_parameter'].get_param('web.base.url'),
        }
        return template_values

    @api.multi
    def _get_email_values(self, template=None):
        self.ensure_one()
        template = template or self._get_template()
        subject = self._get_subject()
        template_values = self._get_template_values()
        values = {
            'email_from': self.env.user.company_id.email,
            'recipient_ids': [(4, self.partner_id.id)],
            'subject': subject,
            'body_html': template.with_context(
                **self._template_context()
            ).render(template_values),
        }
        return values

    def _create_mail_context(self):
        return {
            'notify_only_recipients': True,
        }

    @api.multi
    def _template_context(self):
        self.ensure_one()
        return {
            'lang': self.partner_id.lang,
        }

    @api.multi
    def create_email(self, template=None):
        mail_model = self.env['mail.mail'].with_context(
            **self._create_mail_context())
        created = []
        for item in self:
            if not item.message_ids:
                # useless to create a mail for a digest w/ messages
                # messages could be deleted by admin for instance.
                continue
            values = item.with_context(
                **item._template_context()
            )._get_email_values(template=template)
            item.mail_id = mail_model.create(values)
            created.append(item.id)
        if created:
            logger.info('Create email for digest IDS=%s', str(created))

    @api.model
    def process(self, frequency='daily', domain=None):
        if not domain:
            domain = [
                ('mail_id', '=', False),
                ('partner_id.notify_frequency', '=', frequency),
            ]
        self.search(domain).create_email()
