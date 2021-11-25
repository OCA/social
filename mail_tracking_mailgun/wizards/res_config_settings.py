# Copyright 2021 Tecnativa - Jairo Llopis
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging
from urllib.parse import urljoin

import requests

from odoo import fields, models

_logger = logging.getLogger(__name__)

WEBHOOK_EVENTS = (
    "clicked",
    "complained",
    "delivered",
    "opened",
    "permanent_fail",
    "temporary_fail",
    "unsubscribed",
)


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    mail_tracking_mailgun_enabled = fields.Boolean(
        string="Enable mail tracking with Mailgun",
        help="Enable to enhance mail tracking with Mailgun",
    )
    mail_tracking_mailgun_api_key = fields.Char(
        string="Mailgun API key",
        config_parameter="mailgun.apikey",
        help="Secret API key used to authenticate with Mailgun.",
    )
    mail_tracking_mailgun_webhook_signing_key = fields.Char(
        string="Mailgun webhook signing key",
        config_parameter="mailgun.webhook_signing_key",
        help="Secret key used to validate incoming webhooks payload.",
    )
    mail_tracking_mailgun_validation_key = fields.Char(
        string="Mailgun validation key",
        config_parameter="mailgun.validation_key",
        help="Key used to validate emails.",
    )
    mail_tracking_mailgun_api_url = fields.Char(
        string="Mailgun API endpoint",
        config_parameter="mailgun.api_url",
        help=(
            "Leave this empty if your API endpoint is the default "
            "(https://api.mailgun.net/)."
        ),
    )
    mail_tracking_mailgun_domain = fields.Char(
        string="Mailgun domain",
        config_parameter="mailgun.domain",
        help="Leave empty to use the catch-all domain.",
    )
    mail_tracking_mailgun_webhooks_domain = fields.Char(
        string="Mailgun webhooks domain",
        config_parameter="mailgun.webhooks_domain",
        help="Leave empty to use the base Odoo URL.",
    )
    mail_tracking_mailgun_auto_check_partner_emails = fields.Boolean(
        string="Check partner emails automatically",
        config_parameter="mailgun.auto_check_partner_email",
        help="Attempt to check partner emails always. This may cost money.",
    )

    def get_values(self):
        """Is Mailgun enabled?"""
        result = super().get_values()
        result["mail_tracking_mailgun_enabled"] = bool(
            self.env["ir.config_parameter"].get_param("mailgun.apikey")
        )
        return result

    def mail_tracking_mailgun_unregister_webhooks(self):
        """Remove existing Mailgun webhooks."""
        params = self.env["mail.tracking.email"]._mailgun_values()
        _logger.info("Getting current webhooks")
        webhooks = requests.get(
            urljoin(params.api_url, "/v3/domains/%s/webhooks" % params.domain),
            auth=("api", params.api_key),
        )
        webhooks.raise_for_status()
        for event, data in webhooks.json()["webhooks"].items():
            # Modern webhooks return a list of URLs; old ones just one
            urls = []
            if "urls" in data:
                urls.extend(data["urls"])
            elif "url" in data:
                urls.append(data["url"])
            _logger.info(
                "Deleting webhooks. Event: %s. URLs: %s", event, ", ".join(urls)
            )
            response = requests.delete(
                urljoin(
                    params.api_url,
                    "/v3/domains/%s/webhooks/%s" % (params.domain, event),
                ),
                auth=("api", params.api_key),
            )
            response.raise_for_status()

    def mail_tracking_mailgun_register_webhooks(self):
        """Register Mailgun webhooks to get mail statuses automatically."""
        params = self.env["mail.tracking.email"]._mailgun_values()
        for event in WEBHOOK_EVENTS:
            odoo_webhook = urljoin(
                params.webhooks_domain,
                "/mail/tracking/mailgun/all?db=%s" % self.env.cr.dbname,
            )
            _logger.info("Registering webhook. Event: %s. URL: %s", event, odoo_webhook)
            response = requests.post(
                urljoin(params.api_url, "/v3/domains/%s/webhooks" % params.domain),
                auth=("api", params.api_key),
                data={"id": event, "url": [odoo_webhook]},
            )
            # Assert correct registration
            response.raise_for_status()
