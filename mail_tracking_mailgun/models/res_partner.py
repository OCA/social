# Copyright 2016 Tecnativa - Antonio Espinosa
# Copyright 2016 Tecnativa - Carlos Dauden
# Copyright 2017 Tecnativa - Pedro M. Baeza
# Copyright 2017 Tecnativa - David Vidal
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from urllib.parse import urljoin

import requests

from odoo import _, api, models
from odoo.exceptions import UserError


class ResPartner(models.Model):
    _inherit = "res.partner"

    def email_bounced_set(self, tracking_emails, reason, event=None):
        res = super().email_bounced_set(tracking_emails, reason, event=event)
        self._email_bounced_set(reason, event)
        return res

    def _email_bounced_set(self, reason, event):
        for partner in self:
            if not partner.email:
                continue
            event = event or self.env["mail.tracking.event"]
            event_str = """
                <a href="#"
                   data-oe-model="mail.tracking.event" data-oe-id="%d">%s</a>
            """ % (
                event.id or 0,
                event.id or _("unknown"),
            )
            body = _(
                "Email has been bounced: %(email)s\nReason: %(reason)s\nEvent: %(event_str)s"
            ) % ({"email": partner.email, "reason": reason, "event_str": event_str})
            partner.message_post(body=body)

    def check_email_validity(self):
        """
        Checks mailbox validity with Mailgun's API
        API documentation:
        https://documentation.mailgun.com/en/latest/api-email-validation.html
        """
        params = self.env["mail.tracking.email"]._mailgun_values()
        if not params.validation_key:
            raise UserError(
                _(
                    "You need to configure mailgun.validation_key"
                    " in order to be able to check mails validity"
                )
            )
        for partner in self.filtered("email"):
            res = requests.get(
                urljoin(params.api_url, "/v3/address/validate"),
                auth=("api", params.validation_key),
                params={"address": partner.email, "mailbox_verification": True},
            )
            if (
                not res
                or res.status_code != 200
                and not self.env.context.get("mailgun_auto_check")
            ):
                raise UserError(
                    _(
                        "Error %s trying to check mail" % res.status_code
                        or "of connection"
                    )
                )
            content = res.json()
            if "mailbox_verification" not in content:
                if not self.env.context.get("mailgun_auto_check"):
                    raise UserError(
                        _(
                            "Mailgun Error. Mailbox verification value wasn't"
                            " returned"
                        )
                    )
            # Not a valid address: API sets 'is_valid' as False
            # and 'mailbox_verification' as None
            if not content["is_valid"]:
                partner.email_bounced = True
                body = (
                    _(
                        "%s is not a valid email address. Please check it"
                        " in order to avoid sending issues"
                    )
                    % partner.email
                )
                if not self.env.context.get("mailgun_auto_check"):
                    raise UserError(body)
                partner.message_post(body=body)
            # If the mailbox is not valid API returns 'mailbox_verification'
            # as a string with value 'false'
            if content["mailbox_verification"] == "false":
                partner.email_bounced = True
                body = (
                    _(
                        "%s failed the mailbox verification. Please check it"
                        " in order to avoid sending issues"
                    )
                    % partner.email
                )
                if not self.env.context.get("mailgun_auto_check"):
                    raise UserError(body)
                partner.message_post(body=body)
            # If Mailgun can't complete the validation request the API returns
            # 'mailbox_verification' as a string set to 'unknown'
            if content["mailbox_verification"] == "unknown":
                if not self.env.context.get("mailgun_auto_check"):
                    raise UserError(
                        _(
                            "%s couldn't be verified. Either the request couln't"
                            " be completed or the mailbox provider doesn't "
                            "support email verification"
                        )
                        % (partner.email)
                    )

    def check_email_bounced(self):
        """
        Checks if the partner's email is in Mailgun's bounces list
        API documentation:
        https://documentation.mailgun.com/en/latest/api-suppressions.html
        """
        api_key, api_url, domain, *__ = self.env[
            "mail.tracking.email"
        ]._mailgun_values()
        for partner in self:
            res = requests.get(
                urljoin(api_url, "/v3/%s/bounces/%s" % (domain, partner.email)),
                auth=("api", api_key),
            )
            if res.status_code == 200 and not partner.email_bounced:
                partner.email_bounced = True
            elif res.status_code == 404 and partner.email_bounced:
                partner.email_bounced = False

    def force_set_bounced(self):
        """
        Forces partner's email into Mailgun's bounces list
        API documentation:
        https://documentation.mailgun.com/en/latest/api-suppressions.html
        """
        api_key, api_url, domain, *__ = self.env[
            "mail.tracking.email"
        ]._mailgun_values()
        for partner in self:
            res = requests.post(
                urljoin(api_url, "/v3/%s/bounces" % domain),
                auth=("api", api_key),
                data={"address": partner.email},
            )
            partner.email_bounced = res.status_code == 200 and not partner.email_bounced

    def force_unset_bounced(self):
        """
        Forces partner's email deletion from Mailgun's bounces list
        API documentation:
        https://documentation.mailgun.com/en/latest/api-suppressions.html
        """
        api_key, api_url, domain, *__ = self.env[
            "mail.tracking.email"
        ]._mailgun_values()
        for partner in self:
            res = requests.delete(
                urljoin(api_url, "/v3/%s/bounces/%s" % (domain, partner.email)),
                auth=("api", api_key),
            )
            if res.status_code in (200, 404) and partner.email_bounced:
                partner.email_bounced = False

    def _autocheck_partner_email(self):
        for partner in self:
            partner.with_context(mailgun_auto_check=True).check_email_validity()

    @api.model
    def create(self, vals):
        if "email" in vals and self.env["ir.config_parameter"].sudo().get_param(
            "mailgun.auto_check_partner_email"
        ):
            self._autocheck_partner_email()
        return super().create(vals)

    def write(self, vals):
        if "email" in vals and self.env["ir.config_parameter"].sudo().get_param(
            "mailgun.auto_check_partner_email"
        ):
            self._autocheck_partner_email()
        return super().write(vals)
