# -*- coding: utf-8 -*-
# © 2017 Phuc.nt - <phuc.nt@komit-consulting.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging
from email.utils import formataddr

from odoo import api, fields, models
from odoo import tools


class MailMail(models.Model):
    _inherit = 'mail.mail'

    split_mail_by_recipients = fields.Selection([
        ('split', 'One mail for each recipient'),
        ('merge', 'One mail for all recipients'),
        ('default', 'Project Default')],
        string='Split mail by recipient partner',
        default='default',
    )

    @api.multi
    def send_get_mail_to(self, partner=None):
        self.ensure_one()
        email_to = super(MailMail, self).send_get_mail_to(partner=partner)

        if self._context.get('merge_mail'):
            email_to = [formataddr((p.name, p.email))
                        for p in self.recipient_ids]
            if self.email_to:
                email_to += tools.email_split_and_format(self.email_to)
            logging.info('Merge email_to and recipients to %s', email_to)
        return email_to

    @api.multi
    def send_get_email_dict(self, partner=None):
        self.ensure_one()
        res = super(MailMail, self).send_get_email_dict(partner=partner)

        default = self.env['ir.config_parameter'].get_param(
            'default_mail_split_by_partner_conf')

        # check option merge or split recipients
        send_type = self.split_mail_by_recipients
        if send_type == 'merge' or send_type == 'default' and \
                        default == 'merge':
            email_to = []
            if self.recipient_ids and partner == self.recipient_ids[0] or \
                    (not self.recipient_ids and self.email_to):
                email_to = self.with_context(
                    {'merge_mail': True}).send_get_mail_to(partner=partner)
            res.update({'email_to': email_to})
        return res
