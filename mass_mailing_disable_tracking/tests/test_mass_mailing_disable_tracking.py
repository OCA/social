# SPDX-FileCopyrightText: 2025 hugues de keyzer
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from markupsafe import Markup

from odoo import Command
from odoo.tests.common import TransactionCase

from odoo.addons.mass_mailing_disable_tracking.models.res_config_settings import (
    TRACK_LINKS_PARAMETER,
    TRACK_OPEN_PARAMETER,
)


class TestMassMailingDisableTracking(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.test_mailing_list = cls.env["mailing.list"].create(
            {
                "name": "dummy test mailing list",
            }
        )
        cls.test_mailing_contact = cls.env["mailing.contact"].create(
            {
                "name": "dummy test mailing contact",
                "email": "test@example.net",
                "list_ids": [Command.set([cls.test_mailing_list.id])],
            }
        )
        cls.markup = Markup(
            '<p>hello, <a href="https://odoo-community.org/">this is a link</a></p>'
            "<p>this is not a link: https://odoo-community.org/</p>"
            '<p><a href="https://odoo-community.org/r/some_page">'
            "this is a link that looks like a tracking link</a></p>"
        )
        cls.test_mailing_mailing = cls.env["mailing.mailing"].create(
            {
                "name": "dummy test mailing mailing",
                "subject": "dummy test subject",
                "contact_list_ids": [Command.set([cls.test_mailing_list.id])],
                "body_html": cls.markup,
                "keep_archives": True,
            }
        )
        cls.base_url = cls.env["ir.config_parameter"].get_param("web.base.url")

    def _get_last_mail_id(self):
        return self.env["mail.mail"].search([], order="id desc", limit=1).id

    def _get_new_mail_messages(self, last_mail_id):
        return self.env["mail.mail"].search([("id", ">", last_mail_id or 0)])

    def _send_mail(self):
        last_mail_id = self._get_last_mail_id()
        self.test_mailing_mailing.action_send_mail()
        mail_mail = self._get_new_mail_messages(last_mail_id)
        # the tracking image is only added when actually sending the message:
        # mail.mail._send_prepare_values() is called and the result is sent
        # (but not saved). compute the sent value by ._send_prepare_values()
        # directly.
        return mail_mail._send_prepare_values()

    def test_disable_tracking(self):
        self.env["ir.config_parameter"].set_param(TRACK_OPEN_PARAMETER, False)
        self.env["ir.config_parameter"].set_param(TRACK_LINKS_PARAMETER, False)
        mail = self._send_mail()
        # nothing should be transformed. this includes links starting with /r/
        # that must not get a mailing.track id appended to them.
        self.assertRegex(str(mail["body"]), rf"<body>\s*?{str(self.markup)}\s*?</body>")

    def test_disable_tracking_with_special_links(self):
        self.env["ir.config_parameter"].set_param(TRACK_OPEN_PARAMETER, False)
        self.env["ir.config_parameter"].set_param(TRACK_LINKS_PARAMETER, False)
        self.test_mailing_mailing.body_html = Markup(
            str(self.markup)
            + '<p><a href="/unsubscribe_from_list">this is an unsubscribe link</a></p>'
            '<p><a href="/view">this is a view link</a></p>'
            '<p><a href="/some_page">this is a local link</a></p>'
        )
        mail = self._send_mail()
        # unsubscribe and view links should still be converted and local links
        # should become full urls.
        self.assertRegex(
            str(mail["body"]),
            rf"<body>\s*?{str(self.markup)}"
            rf'<p><a href="{self.base_url}.*?/mailing/\d+/\w*?unsubscribe\?.+">'
            "this is an unsubscribe link</a></p>"
            rf'<p><a href="{self.base_url}/mailing/\d+/view\?.+">'
            "this is a view link</a></p>"
            f'<p><a href="{self.base_url}/some_page">'
            rf"this is a local link</a></p>\s*?</body>",
        )

    def test_enable_open_tracking_only(self):
        self.env["ir.config_parameter"].set_param(TRACK_OPEN_PARAMETER, True)
        self.env["ir.config_parameter"].set_param(TRACK_LINKS_PARAMETER, False)
        mail = self._send_mail()
        # check that the tracking image is present.
        self.assertRegex(
            str(mail["body"]),
            rf"<body>\s*?{str(self.markup)}\s*?"
            rf'<img src="{self.base_url}/mail/track/\d+/\w+/blank\.gif"/>\s*?</body>',
        )

    def test_enable_links_tracking_only(self):
        self.env["ir.config_parameter"].set_param(TRACK_OPEN_PARAMETER, False)
        self.env["ir.config_parameter"].set_param(TRACK_LINKS_PARAMETER, True)
        mail = self._send_mail()
        # check that links are correctly converted.
        self.assertRegex(
            str(mail["body"]),
            rf'<a href="{self.base_url}/r/\w+/m/\d+">this is a link</a>.+?'
            "this is not a link: https://odoo-community.org/.+?"
            rf'<a href="{self.base_url}/r/\w+/m/\d+">this is a link that '
            "looks like a tracking link</a>",
        )

    def test_enable_tracking(self):
        self.env["ir.config_parameter"].set_param(TRACK_OPEN_PARAMETER, True)
        self.env["ir.config_parameter"].set_param(TRACK_LINKS_PARAMETER, True)
        mail = self._send_mail()
        # should work as if the module is not installed.
        self.assertRegex(
            str(mail["body"]),
            rf'<a href="{self.base_url}/r/\w+/m/\d+">this is a link</a>.+?'
            "this is not a link: https://odoo-community.org/.+?"
            rf'<a href="{self.base_url}/r/\w+/m/\d+">this is a link that '
            r"looks like a tracking link</a>.+?\s*?"
            rf'<img src="{self.base_url}/mail/track/\d+/\w+/blank\.gif"/>\s*?</body>',
        )
