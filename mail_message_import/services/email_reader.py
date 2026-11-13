# Copyright 2026 Binhex
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""Read the emails forwarded as files: Outlook (.msg) and standard (.eml).

Messages often bring an email forwarded from a mailbox: what matters is in a
file attached to it, and its headers tell who sent it. An email gives its
headers and body as text, and its real attachments as files; the images of the
signatures (logos, icons) are left out. Attached emails are read too.
"""

import email
import re
from dataclasses import dataclass, field
from email import policy

from odoo.tools import html2plaintext

try:
    import extract_msg
except ImportError:  # pragma: no cover
    extract_msg = None

MSG = "application/vnd.ms-outlook"
EML = "message/rfc822"
EMAIL_TYPES = {MSG, EML}

# Names of the streams of an Outlook email, in the directory of the file.
OUTLOOK_MARK = "__substg1.0_".encode("utf-16-le")
OLE_SIGNATURE = b"\xd0\xcf\x11\xe0"
EMAIL_HEADER = re.compile(
    rb"^(Received|Return-Path|From|To|Subject|Date|MIME-Version|Message-ID"
    rb"|Delivered-To|X-[\w-]+):",
    re.IGNORECASE | re.MULTILINE,
)

# Images smaller than this are logos and icons of signatures, not documents.
MIN_IMAGE_BYTES = 20 * 1024
# Attached emails read inside an email.
MAX_DEPTH = 3
# Long tracking links of the mail filters add nothing to a message.
NOISY_LINK = re.compile(r"<https?://[^>\s]{60,}>")
BLANK_LINES = re.compile(r"\n\s*\n(\s*\n)+")


class EmailError(Exception):
    """The email cannot be read; the first argument is the code of the reason."""


@dataclass
class EmailFile:
    name: str
    data: bytes


@dataclass
class EmailContent:
    text: str = ""
    files: list = field(default_factory=list)


def _is_decoration(name, data):
    """A small image: a logo or an icon of a signature."""
    head = data[:8]
    image = (
        head[:3] == b"\xff\xd8\xff"
        or head.startswith(b"\x89PNG")
        or head[:4] == b"GIF8"
        or (name or "").lower().endswith((".jpg", ".jpeg", ".png", ".gif", ".bmp"))
    )
    return image and len(data) < MIN_IMAGE_BYTES


def _clean_body(text):
    text = NOISY_LINK.sub("", text or "").replace("\r\n", "\n")
    return BLANK_LINES.sub("\n\n", text).strip()


def _header_lines(values):
    return [f"{label}: {value}" for label, value in values if value]


def _read_msg(data, depth):
    if extract_msg is None:
        raise EmailError("msg_library")
    content = EmailContent()
    with extract_msg.openMsg(data) as msg:
        body = msg.body or ""
        if not body.strip() and msg.htmlBody:
            html = msg.htmlBody
            body = html2plaintext(
                html.decode("utf-8", "replace") if isinstance(html, bytes) else html
            )
        lines = _header_lines(
            [
                ("Subject", msg.subject),
                ("From", msg.sender),
                ("To", msg.to),
                ("Cc", msg.cc),
                ("Date", msg.date),
            ]
        )
        content.text = "\n".join(lines) + "\n\n" + _clean_body(body)
        for attachment in msg.attachments:
            payload = attachment.data
            name = (
                getattr(attachment, "longFilename", None)
                or getattr(attachment, "shortFilename", None)
                or "attachment"
            )
            if isinstance(payload, bytes | bytearray):
                if not _is_decoration(name, payload):
                    content.files.append(EmailFile(name, bytes(payload)))
            elif payload is not None and depth < MAX_DEPTH:
                # An attached email.
                inner = _read_msg_object(payload, depth + 1)
                content.text += "\n\n--- Attached email ---\n" + inner.text
                content.files += inner.files
    return content


def _read_msg_object(msg, depth):
    """An email attached to an Outlook email, already opened."""
    content = EmailContent()
    body = msg.body or ""
    lines = _header_lines([("Subject", msg.subject), ("From", msg.sender)])
    content.text = "\n".join(lines) + "\n\n" + _clean_body(body)
    for attachment in msg.attachments:
        payload = attachment.data
        name = getattr(attachment, "longFilename", None) or "attachment"
        if isinstance(payload, bytes | bytearray) and not _is_decoration(name, payload):
            content.files.append(EmailFile(name, bytes(payload)))
    return content


def _read_eml(data, depth):
    message = email.message_from_bytes(data, policy=policy.default)
    return _read_eml_message(message, depth)


def _read_eml_message(message, depth):
    content = EmailContent()
    lines = _header_lines(
        [
            ("Subject", message.get("Subject")),
            ("From", message.get("From")),
            ("To", message.get("To")),
            ("Cc", message.get("Cc")),
            ("Date", message.get("Date")),
        ]
    )
    body = message.get_body(preferencelist=("plain", "html"))
    text = ""
    if body is not None:
        text = body.get_content()
        if body.get_content_type() == "text/html":
            text = html2plaintext(text)
    content.text = "\n".join(lines) + "\n\n" + _clean_body(text)
    for part in message.iter_attachments():
        if part.get_content_type() == "message/rfc822":
            if depth < MAX_DEPTH:
                inner_message = part.get_payload(0)
                inner = _read_eml_message(inner_message, depth + 1)
                content.text += "\n\n--- Attached email ---\n" + inner.text
                content.files += inner.files
            continue
        payload = part.get_payload(decode=True) or b""
        name = part.get_filename() or "attachment"
        if payload and not _is_decoration(name, payload):
            content.files.append(EmailFile(name, payload))
    return content


def read_email(data, mimetype):
    """The text and the attached files of an email.

    :raise EmailError: when the library to read it is missing.
    """
    if mimetype == MSG:
        return _read_msg(data, 1)
    return _read_eml(data, 1)


def email_type(data, filename=""):
    """``MSG`` or ``EML`` when the file is an email, ``None`` otherwise."""
    data = data or b""
    name = (filename or "").lower()
    if data.startswith(OLE_SIGNATURE):
        # Word and Excel files share the container of the Outlook emails.
        return MSG if name.endswith(".msg") or OUTLOOK_MARK in data else None
    head = data[:4096]
    if b"\x00" not in head and (
        name.endswith(".eml") or len(EMAIL_HEADER.findall(head)) >= 3
    ):
        return EML
    return None
