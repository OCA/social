# Copyright 2025 Kencove (https://www.kencove.com/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class WizardFetchPages(models.TransientModel):
    _name = "wizard.fetch.pages"
    _description = "Fetch Facebook Pages Wizard"

    page_ids = fields.One2many(
        "wizard.fetch.pages.line",
        "wizard_id",
        string="Select Pages",
        help="Select the Facebook pages you want to connect",
    )
    user_access_token = fields.Char(readonly=True)

    def action_create_accounts(self):
        """Create social.account records for selected pages"""
        _logger.debug("=" * 80)
        _logger.debug("Wizard: Creating accounts for selected pages...")
        _logger.debug(f"Wizard ID: {self.id}")
        _logger.debug(f"Total pages in wizard: {len(self.page_ids)}")

        selected_pages = self.page_ids.filtered(lambda p: p.selected)
        _logger.debug(f"Selected pages count: {len(selected_pages)}")

        created_account_ids = []

        if selected_pages:
            # Prepare pages data from wizard lines (already have all needed data)
            pages_data = []
            for line in selected_pages:
                pages_data.append(
                    {
                        "id": line.page_id,
                        "name": line.page_name,
                        "access_token": line.page_access_token,
                    }
                )
                _logger.debug(
                    f"  - Will create account for: {line.page_name} "
                    f"(ID: {line.page_id})"
                )

            # Get app credentials from wizard.social.account if available
            wizard_social_account = self.env["wizard.social.account"].search_fetch(
                [("media_type", "=", "facebook")],
                ["facebook_app_id", "facebook_app_secret"],
                order="id desc",
                limit=1,
            )

            # Save app credentials to system settings for reuse
            if wizard_social_account and wizard_social_account.facebook_app_id:
                _logger.debug(
                    "Saving App ID and Secret to system settings for reuse..."
                )
                self.env["ir.config_parameter"].sudo().set_param(
                    "social_media_base.facebook_app_id",
                    wizard_social_account.facebook_app_id,
                )
                if wizard_social_account.facebook_app_secret:
                    self.env["ir.config_parameter"].sudo().set_param(
                        "social_media_base.facebook_app_secret",
                        wizard_social_account.facebook_app_secret,
                    )
                self.env["ir.config_parameter"].sudo().set_param(
                    "social_media_base.facebook_connection_method", "app"
                )
                _logger.debug("App credentials saved to settings")

            # Create accounts using the data we already have
            created_account_ids = self.env[
                "social.account"
            ].create_account_facebook_from_wizard(
                pages_data, self.user_access_token, wizard_social_account
            )
            _logger.debug(f"Account creation completed: {created_account_ids}")
        else:
            _logger.warning("No pages selected!")

        _logger.debug("Redirecting to Facebook accounts list...")
        _logger.debug("=" * 80)

        # Redirect to the list of Facebook accounts with newly created ones highlighted
        return {
            "type": "ir.actions.act_window",
            "name": "Facebook Accounts",
            "res_model": "social.account",
            "view_mode": "list,form",
            "domain": [("media_type", "=", "facebook")],
            "context": {
                "search_default_filter_facebook": 1,
            },
            "target": "current",
        }


class WizardFetchPagesLine(models.TransientModel):
    _name = "wizard.fetch.pages.line"
    _description = "Facebook Page Selection Line"

    wizard_id = fields.Many2one(
        "wizard.fetch.pages", string="Wizard", required=True, ondelete="cascade"
    )
    page_id = fields.Char(string="Page ID", required=True)
    page_name = fields.Char(required=True)
    page_access_token = fields.Char(required=True)
    selected = fields.Boolean(string="Select", default=True)
    already_connected = fields.Boolean(readonly=True)
