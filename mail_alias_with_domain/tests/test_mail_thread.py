# Copyright 2023 Solvti sp. z o.o. (https://solvti.pl)
# Copyright 2025 Therp BV (https://therp.nl)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from email.message import EmailMessage

from odoo.tests import TransactionCase


class TestMailThread(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        ICP = cls.env["ir.config_parameter"].sudo()
        ICP.set_param("mail.catchall.domain", "fsf.org")

        cls.contact_model = cls.env["ir.model"].search([("model", "=", "res.partner")])
        cls.Alias = cls.env["mail.alias"]
        cls.mail_alias_with_domain = cls.Alias.create(
            {
                "alias_entry": "test_alias_entry@example.com",
                "alias_model_id": cls.contact_model.id,
                "alias_defaults": "{'name': 'Test Alias With Domain'}",
            }
        )
        cls.mail_alias_no_domain = cls.Alias.create(
            {
                "alias_entry": "test_alias",
                "alias_model_id": cls.contact_model.id,
                "alias_defaults": "{'name': 'Test Alias No Domain'}",
            }
        )
        message = EmailMessage()
        message.add_header("Subject", "New Alias Test")
        message.add_header("From", "test.user@example.com")
        message.add_header("To", "info@fsf.org")
        message.set_default_type("text/plain")
        message.set_content("Please Create New Contact!")
        cls.message = message

        cls.message_dict = {
            "message_type": "email",
            "message_id": "<ABCDEFGH@1234556789.test.company.com>",
            "subject": "New Contact",
            "email_from": '"test.user@company.com" <test.user@company.com>',
            "from": '"test.user@company.com" <test.user@company.com>',
            "cc": "",
            "partner_ids": [],
            "references": "",
            "in_reply_to": "",
            "date": "2021-09-23 09:03:13",
            "body": "Hello, Please create new contact",
            "attachments": [],
            "bounced_email": False,
            "bounced_partner": "",
            "bounced_msg_id": False,
            "bounced_message": "",
        }

    def test_patch_alias_vals(self):
        # Non default domain in alias_entry.
        vals = {"alias_entry": "test_patch@example.com"}
        self.Alias._patch_alias_vals(vals)
        self.assertEqual(vals["alias_name"], "test_patch__at__example.com")
        # Default domain in alias_entry.
        vals = {"alias_entry": "test_patch@fsf.org"}
        self.Alias._patch_alias_vals(vals)
        self.assertEqual(vals["alias_name"], "test_patch")
        # No domain in alias_entry.
        vals = {"alias_entry": "test_patch"}
        self.Alias._patch_alias_vals(vals)
        self.assertEqual(vals["alias_name"], "test_patch")

    def test_create_alias_by_alias_entry(self):
        self.assertEqual(
            self.mail_alias_with_domain.alias_name, "test_alias_entry__at__example.com"
        )
        self.assertEqual(self.mail_alias_with_domain.alias_domain, "example.com")
        self.assertEqual(self.mail_alias_no_domain.alias_name, "test_alias")
        self.assertEqual(self.mail_alias_no_domain.alias_domain, "fsf.org")

    def test_create_alias_by_alias_name(self):
        alias_with_domain = self.Alias.create(
            {
                "alias_name": "test_alias_name__at__example.com",
                "alias_model_id": self.contact_model.id,
                "alias_defaults": "{'name': 'Test Alias Name'}",
            }
        )
        self.assertEqual(alias_with_domain.alias_entry, "test_alias_name@example.com")
        self.assertEqual(alias_with_domain.alias_domain, "example.com")
        alias_no_domain = self.Alias.create(
            {
                "alias_name": "test_alias_no_domain",
                "alias_model_id": self.contact_model.id,
                "alias_defaults": "{'name': 'Test Alias'}",
            }
        )
        self.assertEqual(alias_no_domain.alias_entry, "test_alias_no_domain")
        self.assertEqual(alias_no_domain.alias_domain, "fsf.org")

    def test_find_alias_with_domain(self):
        email_to = "test_alias_entry@example.com"
        self.message_dict.update(
            {
                "recipients": f'"{email_to}" <{email_to}>',
                "to": f"""
                    "{email_to}" <{email_to}>, "someone@test-fake.com" <someone@test-fake.com>
                """,
            }
        )
        Thread = self.env["mail.thread"]
        matching_alias = Thread._find_alias_with_domain(self.message_dict)
        self.assertEqual(matching_alias, self.mail_alias_with_domain)

    def test_message_route_include_domain_alias(self):
        email_to = "test_alias_entry@example.com"
        self.message.replace_header("To", email_to)
        self.message_dict.update(
            {
                "recipients": f'"{email_to}" <{email_to}>',
                "to": f"""
                    "{email_to}" <{email_to}>, "someone@test-fake.com" <someone@test-fake.com>
                """,
            }
        )
        routes = self.env["mail.thread"].message_route(
            self.message,
            self.message_dict,
            model=self.contact_model.model,
            thread_id=None,
            custom_values=None,
        )
        self.assertEqual(len(routes), 1)  # Will only use route with domain.
        self.assertEqual(routes[0][4], self.mail_alias_with_domain)

    def test_message_route_different_domain_alias(self):
        email_to = "test_alias_entry@something_else.com"
        self.message.replace_header("To", email_to)
        self.message_dict.update(
            {
                "recipients": f'"{email_to}" <{email_to}>',
                "to": (
                    f'"{email_to}" <{email_to}>, '
                    '"someone@test-fake.com" <someone@test-fake.com>'
                ),
            }
        )
        routes = self.env["mail.thread"].message_route(
            self.message,
            self.message_dict,
            model=self.contact_model.model,
            thread_id=None,
            custom_values=None,
        )
        self.assertEqual(len(routes), 1)  # Should be default route
        self.assertEqual(routes[0][0], self.contact_model.model)
        self.assertEqual(routes[0][4], None)

    def test_message_route_two_types_of_aliases_at_once(self):
        email_to_1 = "test_alias_entry@example.com"
        email_to_2 = "test_alias@example_mail.com"
        self.message.replace_header("To", f"{email_to_1}, {email_to_2}")
        self.message_dict.update(
            {
                "recipients": f'"{email_to_1}" <{email_to_1}>, "{email_to_2}" <{email_to_2}>',
                "to": (
                    f'"{email_to_1}" <{email_to_1}>, "{email_to_2}" <{email_to_2}>,'
                    '"abc@abc.com" <abc@abc.com>'
                ),
            }
        )
        routes = self.env["mail.thread"].message_route(
            self.message,
            self.message_dict,
            model=self.contact_model.model,
            thread_id=None,
            custom_values=None,
        )
        self.assertEqual(len(routes), 1)  # Will only use route with domain.
        self.assertEqual(routes[0][4], self.mail_alias_with_domain)

    def test_message_route_no_domain_alias(self):
        email_to = "test_alias@example_mail.com"
        self.message.replace_header("To", f"{email_to}")
        self.message_dict.update(
            {
                "recipients": f'"{email_to}" <{email_to}>',
                "to": f'"{email_to}" <{email_to}>, "abc@abc.com" <abc@abc.com>',
            }
        )
        routes = self.env["mail.thread"].message_route(
            self.message,
            self.message_dict,
            model=self.contact_model.model,
            thread_id=None,
            custom_values=None,
        )
        self.assertEqual(len(routes), 1)  # Will only use route without domain.
        self.assertEqual(routes[0][4], self.mail_alias_no_domain)
