# Copyright 2026 Binhex
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""Small helpers shared by the models of the module."""

import re
import threading

# Context key set while the module acts on its own (webhooks, scheduled
# actions), for the processors to tell it from the changes of a person.
AUTOMATION_CONTEXT_KEY = "mail_message_import_automation"

CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def automation_user(env, company):
    """User the module acts as in ``company``.

    The person that triggered the action when there is one; when the module
    acts on its own (webhooks, scheduled actions), its agent if a module sets
    one that works in the company (``mail.message.import.config._agent_user``),
    otherwise OdooBot.
    """
    root = env.ref("base.user_root")
    if env.user != root:
        return env.user
    return env["mail.message.import.config"]._agent_user(company) or root


def clean_text(value, max_length=None):
    """Plain text without control characters, ``""`` when it is not text."""
    if not isinstance(value, str):
        return ""
    value = CONTROL_CHARS.sub("", value).strip()
    if max_length and len(value) > max_length:
        value = value[:max_length]
    return value


def commit_progress(env):
    """Commit the work of a cron step; tests run in one transaction instead."""
    if not getattr(threading.current_thread(), "testing", False):
        env.cr.commit()  # pylint: disable=invalid-commit


def truncate(value, length=2000):
    value = value or ""
    return value if len(value) <= length else value[: length - 3] + "..."
