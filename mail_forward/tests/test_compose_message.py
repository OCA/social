# -*- coding: utf-8 -*-
# © 2014-2015 Grupo ESOC <www.grupoesoc.es>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from os import path
from openerp.tests.common import TransactionCase


class ForwardMailCase(TransactionCase):
    def setUp(self, *args, **kwargs):
        super(ForwardMailCase, self).setUp(*args, **kwargs)
        self.compose = self.env["mail.compose.message"].create({})
        self.fwd = self.env["mail_forward.compose_message"].create({
            "original_wizard_id": self.compose.id,
        })
        self.partner = self.env["res.partner"].create({"name": __file__})
        self.attachment = self.env["ir.attachment"].create({
            "name": "Testing source",
            "datas_fname": path.basename(__file__),
            "type": "url",
            "url": "file://%s" % __file__,
        })

    def test_subject(self):
        """Test correct subject is used."""
        self.compose.subject = "Bad subject"
        good = "Good subject"
        defaults = self.fwd.with_context(default_subject=good).default_get(
            ["subject"])
        self.assertEqual(defaults["subject"], good)

    def test_change_destination(self):
        """Test what happens when changing the destination."""
        model = self.env["ir.model"].search(
            [("model", "=", self.partner._name)])

        # Set a partner as destination object
        self.fwd.destination_object_id = self.partner
        self.fwd.change_destination_object()

        self.assertEqual(self.fwd.model, self.partner._name)
        self.assertEqual(self.fwd.res_id, self.partner.id)
        self.assertEqual(self.fwd.record_name,
                         "%s %s" % (model.name, self.partner.name))

        # Remove the destination object
        self.fwd.destination_object_id = False
        self.fwd.change_destination_object()

        self.assertFalse(self.fwd.model)
        self.assertFalse(self.fwd.res_id)
        self.assertFalse(self.fwd.record_name)

    def test_move_attachments(self):
        """Attachments moved correctly."""
        self.fwd.attachment_ids |= self.attachment
        self.fwd.destination_object_id = self.partner
        self.fwd.change_destination_object()
        self.fwd.body = "body"
        self.fwd.subject = "subject"
        self.fwd.move_attachments = True
        self.fwd.send_mail()

        self.assertEqual(self.attachment.res_model, self.partner._name)
        self.assertEqual(self.attachment.res_id, self.partner.id)
