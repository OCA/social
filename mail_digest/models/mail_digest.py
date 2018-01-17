# Copyright 2017-2018 Camptocamp - Simone Orsi
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import fields, models, api, exceptions, _

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
    user_id = fields.Many2one(
        string='User',
        comodel_name='res.users',
        readonly=True,
        required=True,
        ondelete='cascade',
    )
    frequency = fields.Selection(
        related='user_id.digest_frequency',
        readonly=True,
    )
    message_ids = fields.Many2many(
        comodel_name='mail.message',
        string='Messages'
    )
    mail_id = fields.Many2one(
        'mail.mail',
        'Mail',
        ondelete='set null',
    )
    state = fields.Selection(related='mail_id.state', readonly=True)
    # To my future self: never ever change this field to `template_id`.
    # When creating digest records within the context of mail composer
    # (and possibly other contexts) you'll have a `default_template_id`
    # key in the context which is going to override our safe default.
    # This is going to break email generation because the template
    # will be completely wrong. Lesson learned :)
    digest_template_id = fields.Many2one(
        'ir.ui.view',
        'Qweb mail template',
        ondelete='set null',
        default=lambda self: self._default_digest_template_id(),
        domain=[('type', '=', 'qweb')],
    )

    def _default_digest_template_id(self):
        """Retrieve default template to render digest."""
        return self.env.ref('mail_digest.default_digest_tmpl',
                            raise_if_not_found=False)

    @api.multi
    @api.depends("user_id", "user_id.digest_frequency")
    def _compute_name(self):
        for rec in self:
            rec.name = '{} - {}'.format(
                rec.user_id.name, rec._get_subject())

    @api.model
    def create_or_update(self, partners, message):
        """Create or update digest.

        :param partners: recipients as `res.partner` browse list
        :param message: `mail.message` to include in digest
        """
        for partner in partners:
            digest = self._get_or_create_by_user(partner.real_user_id)
            digest.message_ids |= message
        return True

    @api.model
    def _get_by_user(self, user):
        """Retrieve digest record for given user.

        :param user: `res.users` browse record

        By default we lookup for pending digest without notification yet.
        """
        domain = [
            ('user_id', '=', user.id),
        ]
        return self.search(domain, limit=1)

    @api.model
    def _get_or_create_by_user(self, user):
        """Retrieve digest record or create it by user.

        :param user: `res.users` record to create/get digest for
        """
        existing = self._get_by_user(user)
        if existing:
            return existing
        values = {'user_id': user.id, }
        return self.create(values)

    @api.model
    def _message_group_by_key(self, msg):
        """Return the key to group messages by."""
        return msg.subtype_id.id

    @api.multi
    def _message_group_by(self):
        """Group digest messages.

        A digest can contain several messages.
        To display them in a nice and organized form in your emails
        we group them by subtype by default.
        """
        self.ensure_one()
        grouped = {}
        for msg in self.message_ids:
            grouped.setdefault(self._message_group_by_key(msg), []).append(msg)
        return grouped

    def _get_site_name(self):
        """Retrieve site name for meaningful mail subject.

        If you run a website we get website's name
        otherwise we default to current user's company name.
        """
        # default to company
        name = self.env.user.company_id.name
        if 'website' in self.env:
            # TODO: shall we make this configurable at digest or global level?
            # Maybe you have a website but
            # your digest msgs are not related to it at all or partially.
            ws = None
            try:
                ws = self.env['website'].get_current_website()
                name = ws.name
            except RuntimeError:
                # RuntimeError: object unbound -> no website request.
                # Fallback to default website if any.
                ws = self.env['website'].search([], limit=1)
            if ws:
                name = ws.name
        return name

    @api.multi
    def _get_subject(self):
        """Build the full subject for digest's mail."""
        # TODO: shall we move this to computed field?
        self.ensure_one()
        subject = '[{}] '.format(self._get_site_name())
        if self.user_id.digest_frequency == 'daily':
            subject += _('Daily update')
        elif self.user_id.digest_frequency == 'weekly':
            subject += _('Weekly update')
        return subject

    @api.multi
    def _get_template_values(self):
        """Collect variables to render digest's template."""
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
        """Collect variables to create digest's mail message."""
        self.ensure_one()
        template = template or self.digest_template_id
        if not template:
            raise exceptions.UserError(_(
                'You must pass a template or set one on the digest record.'
            ))
        subject = self._get_subject()
        template_values = self._get_template_values()
        values = {
            'email_from': self.env.user.company_id.email,
            'recipient_ids': [(4, self.user_id.partner_id.id)],
            'subject': subject,
            'body_html': template.with_context(
                **self._template_context()
            ).render(template_values),
        }
        return values

    def _create_mail_context(self):
        """Inject context vars.

        By default we make sure that digest's email
        will have only digest's user among recipients.
        """
        return {
            'notify_only_recipients': True,
        }

    @api.multi
    def _template_context(self):
        """Rendering context for digest's template.

        By default we enforce user's language.
        """
        self.ensure_one()
        return {
            'lang': self.user_id.lang,
        }

    @api.multi
    def create_email(self, template=None):
        """Create `mail.message` records for current digests.

        :param template: qweb template instance to override default digest one.
        """
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
        return created

    @api.multi
    def action_create_email(self):
        return self.create_email()

    @api.model
    def process(self, frequency='daily', domain=None):
        """Process existing digest records to create emails via cron.

        :param frequency: lookup digest records by users' `digest_frequency`
        :param domain: pass custom domain to lookup only specific digests
        """
        if not domain:
            domain = [
                ('mail_id', '=', False),
                ('user_id.digest_frequency', '=', frequency),
            ]
        self.search(domain).create_email()
