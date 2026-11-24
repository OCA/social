# Copyright 2026 Binhex
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from email.message import EmailMessage
from types import SimpleNamespace
from unittest.mock import patch

from odoo.tests import tagged

from ..services import email_reader
from ..services.email_reader import EML, MSG, EmailError, email_type, read_email
from ..services.tools import automation_user, clean_text
from .common import MailMessageImportCase

DOCUMENT = b"%PDF-1.4 " + b"1" * 30000
LOGO = b"\x89PNG" + b"0" * 100


class FakeOutlookEmail(SimpleNamespace):
    """An Outlook email as the library opens it."""

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False


@tagged("post_install", "-at_install")
class TestEmailReader(MailMessageImportCase):
    """The emails forwarded as files are told apart and read."""

    def test_type_of_the_files(self):
        ole = email_reader.OLE_SIGNATURE + b"\x00" * 100
        self.assertEqual(email_type(ole, "FW Order.MSG"), MSG)
        self.assertEqual(email_type(ole + email_reader.OUTLOOK_MARK), MSG)
        self.assertIsNone(email_type(ole, "order.doc"), "A Word file")
        headers = b"From: a@example.com\nTo: b@example.com\nSubject: Order\n\nHi"
        self.assertEqual(email_type(headers), EML)
        self.assertEqual(email_type(b"Hi", "order.eml"), EML)
        self.assertIsNone(email_type(b"Just a text", "notes.txt"))
        self.assertIsNone(email_type(None))

    def test_html_email_with_an_attached_email(self):
        inner = EmailMessage()
        inner["From"] = "vendor@example.com"
        inner["Subject"] = "Quote"
        inner.set_content("The quote is attached.")
        inner.add_attachment(
            DOCUMENT, maintype="application", subtype="pdf", filename="quote.pdf"
        )
        outer = EmailMessage()
        outer["From"] = "buyer@example.com"
        outer["Subject"] = "FW: Quote"
        outer.set_content("<p>Please order it.</p>", subtype="html")
        outer.add_attachment(LOGO, maintype="image", subtype="png", filename="logo.png")
        outer.add_attachment(inner)
        content = read_email(outer.as_bytes(), EML)
        self.assertIn("Subject: FW: Quote", content.text)
        self.assertIn("Please order it.", content.text)
        self.assertIn("--- Attached email ---", content.text)
        self.assertIn("Subject: Quote", content.text)
        self.assertEqual(
            [(file.name, file.data) for file in content.files],
            [("quote.pdf", DOCUMENT)],
            "The logo of the signature is left out",
        )

    def test_outlook_email_needs_its_library(self):
        with patch.object(email_reader, "extract_msg", None):
            with self.assertRaises(EmailError) as error:
                read_email(b"data", MSG)
        self.assertEqual(error.exception.args, ("msg_library",))

    def test_outlook_email_with_an_attached_email(self):
        inner = SimpleNamespace(
            body="See the prices.",
            subject="Quote",
            sender="vendor@example.com",
            attachments=[
                SimpleNamespace(data=DOCUMENT, longFilename="quote.pdf"),
                SimpleNamespace(data=LOGO, longFilename="logo.png"),
            ],
        )
        outer = FakeOutlookEmail(
            body="",
            htmlBody=b"<p>Please order it.</p>",
            subject="FW: Quote",
            sender="buyer@example.com",
            to="orders@example.com",
            cc=None,
            date="Mon, 2 Nov 2026 10:00:00 +0100",
            attachments=[
                SimpleNamespace(data=LOGO, shortFilename="logo.png"),
                SimpleNamespace(data=bytearray(DOCUMENT)),
                SimpleNamespace(data=inner),
            ],
        )
        library = SimpleNamespace(openMsg=lambda data: outer)
        with patch.object(email_reader, "extract_msg", library):
            content = read_email(b"data", MSG)
        self.assertIn("To: orders@example.com", content.text)
        self.assertNotIn("Cc:", content.text)
        self.assertIn("Please order it.", content.text)
        self.assertIn("--- Attached email ---", content.text)
        self.assertIn("See the prices.", content.text)
        self.assertEqual(
            [file.name for file in content.files], ["attachment", "quote.pdf"]
        )


@tagged("post_install", "-at_install")
class TestTools(MailMessageImportCase):
    def test_automation_user(self):
        admin = self.env.ref("base.user_admin")
        root = self.env.ref("base.user_root")
        self.assertEqual(automation_user(self.env(user=admin), self.company), admin)
        self.assertEqual(
            automation_user(self.env(user=root), self.company),
            root,
            "OdooBot acts when no module sets an agent",
        )

    def test_clean_text(self):
        self.assertEqual(clean_text(None), "")
        self.assertEqual(clean_text(" Ana\x00 López\x07 "), "Ana López")
        self.assertEqual(clean_text("Order 42", max_length=5), "Order")
