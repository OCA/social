# Copyright 2026 nurefexc (https://nurefexc.com)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo.tests.common import TransactionCase


class TestNtfyUrl(TransactionCase):
    def setUp(self):
        super().setUp()
        # Create a test user to verify notification settings
        self.test_user = self.env["res.users"].create(
            {
                "name": "Test Ntfy User",
                "login": "test_ntfy_user",
                "email": "test@nurefexc.com",
                "notification_type": "inbox",  # Default Odoo setting
            }
        )
        # Set a default ntfy server URL in system parameters
        self.env["ir.config_parameter"].sudo().set_param(
            "ntfy.server_url", "https://ntfy.sh"
        )

    def test_01_url_generation_on_write(self):
        """Test if the subscription URL is generated when switching to ntfy"""
        self.test_user.write({"notification_type": "ntfy"})

        # Verify that the URL field is populated
        self.assertTrue(
            self.test_user.ntfy_topic_url,
            "The ntfy subscription URL should not be empty after activation.",
        )
        # Check if it contains the correct server and user reference
        self.assertIn("https://ntfy.sh", self.test_user.ntfy_topic_url)
        self.assertIn(str(self.test_user.id), self.test_user.ntfy_topic_url)

    def test_02_action_regenerate_url(self):
        """Test the manual regeneration action (Reset button)"""
        self.test_user.write({"notification_type": "ntfy"})
        first_url = self.test_user.ntfy_topic_url

        # Call the manual generation method
        self.test_user.action_generate_ntfy_url()
        second_url = self.test_user.ntfy_topic_url

        # Ensure the URL has changed (due to the time-based seed)
        self.assertNotEqual(
            first_url,
            second_url,
            "The URL must change after calling the regeneration action.",
        )

    def test_03_server_url_change_sync(self):
        """Test if the system detects server URL changes and updates user topics"""
        self.test_user.write({"notification_type": "ntfy"})

        # Change the global server URL in settings
        new_server = "https://ntfy.nurefexc.com"
        self.env["ir.config_parameter"].sudo().set_param("ntfy.server_url", new_server)

        # Trigger the consistency check
        self.test_user._check_ntfy_url_consistency()

        # Verify the user"s URL was updated to the new server
        self.assertIn(
            new_server,
            self.test_user.ntfy_topic_url,
            "The user topic URL should reflect the updated server URL.",
        )
