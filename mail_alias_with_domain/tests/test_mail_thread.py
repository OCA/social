# Copyright 2023 Solvti sp. z o.o. (https://solvti.pl)

from email.message import EmailMessage

from odoo.tests import TransactionCase


class TestMailThread(TransactionCase):
    def setUp(self):
        super(TestMailThread, self).setUp()

        self.contact_model = self.env["ir.model"].search(
            [("model", "=", "res.partner")]
        )
        self.mail_alias_with_domain = self.env["mail.alias"].create(
            {
                "check_domain": True,
                "alias_display_name": "test_alias_hash",
                "alias_domain": "example.com",
                "alias_model_id": self.contact_model.id,
                "alias_defaults": "{'name': 'Test Alias Hash'}",
            }
        )
        self.mail_alias = self.env["mail.alias"].create(
            {
                "alias_name": "test_alias",
                "alias_model_id": self.contact_model.id,
                "alias_defaults": "{'name': 'Test Alias'}",
            }
        )

        message = EmailMessage()
        message.add_header("Subject", "New Alias Test")
        message.add_header("From", "test.user@example.com")
        message.set_default_type("text/plain")
        message.set_content("Please Create New Contact!")
        self.message = message

        self.message_dict = {
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

    def test_create_alias_by_alias_name_and_alias_display_name(self):
        self.assertTrue(self.mail_alias_with_domain.alias_name)
        self.assertTrue(self.mail_alias.alias_display_name)

    def test_generate_hash(self):
        alias = self.mail_alias_with_domain
        self.assertEqual(alias.alias_hash, alias.alias_name.split("+")[0])

    def test_message_route_include_hash_alias(self):
        email_to = "test_alias_hash@example.com"
        self.message.add_header("To", email_to)
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
        self.assertTrue(
            any(
                self.mail_alias_with_domain == alias for alias in [r[4] for r in routes]
            )
        )

    def test_message_route_differend_domain_for_hash_alias(self):
        email_to = "test_alias_hash@something_else.com"
        self.message.add_header("To", email_to)
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
        self.assertFalse(
            any(
                self.mail_alias_with_domain == alias for alias in [r[4] for r in routes]
            )
        )

    def test_message_route_two_types_of_aliases_at_once(self):
        email_to_1 = "test_alias_hash@example.com"
        email_to_2 = "test_alias@example_mail.com"
        self.message.add_header("To", f"{email_to_1}, {email_to_2}")
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
        self.assertTrue(
            {r[4] for r in routes} == {self.mail_alias_with_domain, self.mail_alias}
        )
