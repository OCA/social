# Copyright 2025 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging

from odoo import api, fields, models

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
    user_access_token = fields.Char(string="User Access Token", readonly=True)

    def action_create_accounts(self):
        """Create social.account records for selected pages"""
        _logger.info("=" * 80)
        _logger.info("Wizard: Creating accounts for selected pages...")
        _logger.info("Wizard ID: %s", self.id)
        _logger.info("Total pages in wizard: %d", len(self.page_ids))

        selected_pages = self.page_ids.filtered(lambda p: p.selected)
        _logger.info("Selected pages count: %d", len(selected_pages))

        if selected_pages:
            # Prepare pages data from wizard lines (already have all needed data)
            pages_data = []
            for line in selected_pages:
                pages_data.append({
                    "id": line.page_id,
                    "name": line.page_name,
                    "access_token": line.page_access_token,
                })
                _logger.info("  - Will create account for: %s (ID: %s)", line.page_name, line.page_id)

            # Get app credentials from wizard.social.account if available
            wizard_social_account = self.env["wizard.social.account"].search(
                [("media_type", "=", "facebook")], order="id desc", limit=1
            )

            # Create accounts using the data we already have
            self.env["social.account"].create_account_facebook_from_wizard(
                pages_data,
                self.user_access_token,
                wizard_social_account
            )
            _logger.info("Account creation completed")
        else:
            _logger.warning("No pages selected!")

        _logger.info("Closing wizard...")
        _logger.info("=" * 80)
        return {"type": "ir.actions.act_window_close"}


class WizardFetchPagesLine(models.TransientModel):
    _name = "wizard.fetch.pages.line"
    _description = "Facebook Page Selection Line"

    wizard_id = fields.Many2one("wizard.fetch.pages", string="Wizard", required=True, ondelete="cascade")
    page_id = fields.Char(string="Page ID", required=True)
    page_name = fields.Char(string="Page Name", required=True)
    page_access_token = fields.Char(string="Page Access Token", required=True)
    selected = fields.Boolean(string="Select", default=True)
    already_connected = fields.Boolean(string="Already Connected", readonly=True)
