# -*- coding: utf-8 -*-
# Copyright 2016 Tecnativa - Antonio Espinosa
# Copyright 2016 Tecnativa - Carlos Dauden
# Copyright 2017 Tecnativa - Pedro M. Baeza
# Copyright 2017 Tecnativa - David Vidal
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import requests
import json

from openerp import _, api, models
from openerp.exceptions import UserError


class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.multi
    def email_bounced_set(self, tracking_emails, reason, event=None):
        res = super(ResPartner, self).email_bounced_set(
            tracking_emails, reason, event=event)
        self._email_bounced_set(reason, event)
        return res

    @api.multi
    def _email_bounced_set(self, reason, event):
        for partner in self:
            if not partner.email:
                continue
            body = _('Email has been bounced: %s\n'
                     'Reason: %s\n'
                     'Event: %s') % (partner.email, reason,
                                     event['Message-Id'] or '')
            partner.message_post(body=body)

    @api.multi
    def check_email_validity(self):
        """
        Checks mailbox validity with Mailgun's API
        API documentation:
        https://documentation.mailgun.com/en/latest/api-email-validation.html
        """
        api_key, api_url, domain, validation_key = self.env[
            'mail.tracking.email']._mailgun_values()
        if not validation_key:
            raise UserError(_('You need to configure mailgun.validation_key'
                              ' in order to be able to check mails validity'))
        for partner in self:
            res = requests.get(
                "%s/address/validate" % api_url,
                auth=("api", validation_key), params={
                    "address": partner.email,
                    "mailbox_verification": True,
                })
            if not res or res.status_code != 200:
                raise UserError(_(
                    'Error %s trying to '
                    'check mail' % res.status_code or 'of connection'))
            content = json.loads(res.content, res.apparent_encoding)
            if 'mailbox_verification' not in content:
                raise UserError(
                    _("Mailgun Error. Mailbox verification value wasn't"
                      " returned"))
            # Not a valid address: API sets 'is_valid' as False
            # and 'mailbox_verification' as None
            if not content['is_valid']:
                partner.email_bounced = True
                raise UserError(
                    _('%s is not a valid email address. Please check it '
                      'in order to avoid sending issues') % (partner.email))
            # If the mailbox is not valid API returns 'mailbox_verification'
            # as a string with value 'false'
            if content['mailbox_verification'] == 'false':
                partner.email_bounced = True
                raise UserError(
                    _('%s failed the mailbox verification. Please check it '
                      'in order to avoid sending issues') % (partner.email))
            # If Mailgun can't complete the validation request the API returns
            # 'mailbox_verification' as a string set to 'unknown'
            if content['mailbox_verification'] == 'unknown':
                raise UserError(
                    _("%s couldn't be verified. Either the request couln't be "
                      "completed or the mailbox provider doesn't support "
                      "email verification") % (partner.email))

    @api.multi
    def check_email_bounced(self):
        """
        Checks if the partner's email is in Mailgun's bounces list
        API documentation:
        https://documentation.mailgun.com/en/latest/api-suppressions.html
        """
        api_key, api_url, domain, validation_key = self.env[
            'mail.tracking.email']._mailgun_values()
        for partner in self:
            res = requests.get(
                '%s/%s/bounces/%s' % (api_url, domain, partner.email),
                auth=("api", api_key))
            if res.status_code == 200 and not partner.email_bounced:
                partner.email_bounced = True
            elif res.status_code == 404 and partner.email_bounced:
                partner.email_bounced = False

    @api.multi
    def force_set_bounced(self):
        """
        Forces partner's email into Mailgun's bounces list
        API documentation:
        https://documentation.mailgun.com/en/latest/api-suppressions.html
        """
        api_key, api_url, domain, validation_key = self.env[
            'mail.tracking.email']._mailgun_values()
        for partner in self:
            res = requests.post(
                '%s/%s/bounces' % (api_url, domain),
                auth=("api", api_key),
                data={'address': partner.email})
            partner.email_bounced = (
                res.status_code == 200 and not partner.email_bounced)

    @api.multi
    def force_unset_bounced(self):
        """
        Forces partner's email deletion from Mailgun's bounces list
        API documentation:
        https://documentation.mailgun.com/en/latest/api-suppressions.html
        """
        api_key, api_url, domain, validation_key = self.env[
            'mail.tracking.email']._mailgun_values()
        for partner in self:
            res = requests.delete(
                '%s/%s/bounces/%s' % (api_url, domain, partner.email),
                auth=("api", api_key))
            if res.status_code in (200, 404) and partner.email_bounced:
                partner.email_bounced = False
