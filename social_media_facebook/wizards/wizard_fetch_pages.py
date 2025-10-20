# Copyright 2025 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


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
        print("=" * 80)
        print("Wizard: Creating accounts for selected pages...")
        print(f"Wizard ID: {self.id}")
        print(f"Total pages in wizard: {len(self.page_ids)}")

        selected_pages = self.page_ids.filtered(lambda p: p.selected)
        print(f"Selected pages count: {len(selected_pages)}")

        created_account_ids = []

        if selected_pages:
            # Prepare pages data from wizard lines (already have all needed data)
            pages_data = []
            for line in selected_pages:
                pages_data.append({
                    "id": line.page_id,
                    "name": line.page_name,
                    "access_token": line.page_access_token,
                })
                print(f"  - Will create account for: {line.page_name} (ID: {line.page_id})")

            # Get app credentials from wizard.social.account if available
            wizard_social_account = self.env["wizard.social.account"].search(
                [("media_type", "=", "facebook")], order="id desc", limit=1
            )

            # Create accounts using the data we already have
            created_account_ids = self.env["social.account"].create_account_facebook_from_wizard(
                pages_data,
                self.user_access_token,
                wizard_social_account
            )
            print("Account creation completed")
        else:
            print("WARNING: No pages selected!")

        print("Redirecting to Facebook accounts list...")
        print("=" * 80)

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

    wizard_id = fields.Many2one("wizard.fetch.pages", string="Wizard", required=True, ondelete="cascade")
    page_id = fields.Char(string="Page ID", required=True)
    page_name = fields.Char(string="Page Name", required=True)
    page_access_token = fields.Char(string="Page Access Token", required=True)
    selected = fields.Boolean(string="Select", default=True)
    already_connected = fields.Boolean(string="Already Connected", readonly=True)
