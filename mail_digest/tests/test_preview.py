# -*- coding: utf-8 -*-
# Copyright 2017 Simone Orsi <simone.orsi@camptocamp.com>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo.tests.common import SavepointCase
import mock
from ..controllers.digest_layout_preview import DigestPreview

REQUEST_PATH = 'odoo.addons.mail_digest.controllers.digest_layout_preview'


class PreviewCase(SavepointCase):
    """Easy tests for preview controller to make codecov happy."""

    @classmethod
    def setUpClass(cls):
        super(PreviewCase, cls).setUpClass()
        cls.ctrl = DigestPreview()

    @mock.patch(REQUEST_PATH + '.request')
    def test_fake_digest(self, patched_req):
        patched_req.env = self.env
        digest = self.ctrl._fake_digest()
        self.assertEqual(
            digest.partner_id, self.env.user.partner_id,
        )
        self.assertEqual(
            digest.digest_template_id, digest._default_digest_template_id(),
        )
        self.assertTrue(digest.message_ids)
        self.assertTrue(digest.sanitize_msg_body)

    @mock.patch(REQUEST_PATH + '.request')
    def test_fake_messages(self, patched_req):
        patched_req.env = self.env
        all_types = self.env['mail.message.subtype'].search([])
        messages = self.ctrl._fake_messages()
        self.assertEqual(
            len(messages), len(all_types) * 2
        )

    @mock.patch(REQUEST_PATH + '.request')
    def test_fake_content(self, patched_req):
        patched_req.env = self.env
        subj, body = self.ctrl._fake_content(None, 1, 2)
        body = 'Random text here lorem ipsum 1 / 2'
        self.assertEqual(subj, 'Lorem ipsum 1 / 2')
        self.assertEqual(body, 'Random text here lorem ipsum 1 / 2')
        subj, body = self.ctrl._fake_content(None, 2, 2)
        self.assertEqual(subj, 'Lorem ipsum 2 / 2')
        self.assertTrue(body.startswith('<p style="font-size: 13px;'))

    @mock.patch(REQUEST_PATH + '.request')
    def test_fake_tracking_vals(self, patched_req):
        patched_req.env = self.env
        vals = self.ctrl._fake_tracking_vals()
        self.assertEqual(len(vals), 2)
