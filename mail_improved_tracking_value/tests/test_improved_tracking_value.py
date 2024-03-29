# Copyright 2018 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import json

from odoo.tests.common import TransactionCase


class TestImproveTrackingValue(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.model = cls.env["mail.tracking.value"]
        cls.msg = cls.env["mail.message"].create({"message_type": "email"})
        cls.mr = cls.env.ref("base.res_partner_title_mister")
        cls.dr = cls.env.ref("base.res_partner_title_doctor")
        cls.mm = cls.env.ref("base.res_partner_title_madam")
        cls.pf = cls.env.ref("base.res_partner_title_prof")

    def test_change_one2many(self):
        """Test tracking one2many changes"""
        tracking = self.model.create_tracking_values(
            self.mr,
            self.dr,
            "title",
            {"string": "TestingField", "type": "one2many"},
            tracking_sequence=100,
            model_name="res.partner",
        )
        self.assertEqual(tracking["old_value_char"], self.mr.display_name)
        self.assertEqual(tracking["new_value_char"], self.dr.display_name)
        self.assertEqual(tracking["old_value_text"], json.dumps([self.mr.id]))
        self.assertEqual(tracking["new_value_text"], json.dumps([self.dr.id]))

    def test_change_one2many_empty(self):
        """Test tracking one2many changes emtpy"""
        tracking = self.model.create_tracking_values(
            self.mr,
            None,
            "title",
            {"string": "TestingField", "type": "one2many"},
            tracking_sequence=100,
            model_name="res.partner",
        )
        self.assertEqual(tracking["old_value_char"], self.mr.display_name)
        self.assertEqual(tracking["new_value_char"], "")
        self.assertEqual(tracking["old_value_text"], json.dumps([self.mr.id]))
        self.assertEqual(tracking["new_value_text"], json.dumps([]))

    def test_change_many2many(self):
        """Test tracking many2many changes"""
        oldvalue = self.env["res.partner.title"].browse([self.mr.id, self.dr.id])
        newvalue = self.env["res.partner.title"].browse([self.mm.id, self.pf.id])

        tracking = self.model.create_tracking_values(
            oldvalue,
            newvalue,
            "title",
            {"string": "TestingField", "type": "many2many"},
            tracking_sequence=100,
            model_name="res.partner",
        )
        self.assertEqual(
            tracking["old_value_char"],
            self.mr.display_name + ", " + self.dr.display_name,
        )
        self.assertEqual(
            tracking["new_value_char"],
            self.mm.display_name + ", " + self.pf.display_name,
        )
        self.assertEqual(tracking["old_value_text"], json.dumps(oldvalue.ids))
        self.assertEqual(tracking["new_value_text"], json.dumps(newvalue.ids))

    def test_char_tracking_value(self):
        r = self.model.create(
            {
                "mail_message_id": self.msg.id,
                "field_type": "char",
                "old_value_char": "weakness",
                "new_value_char": "strength",
                "field": self.env["ir.model.fields"]._get("res.partner", "name").id,
                "field_desc": "desc",
            }
        )
        self.assertEqual(r.old_value_formatted, "weakness")
        self.assertEqual(r.new_value_formatted, "strength")

    def test_many2many_tracking_value(self):
        r = self.model.create(
            {
                "mail_message_id": self.msg.id,
                "field_type": "many2many",
                "old_value_char": "123",
                "new_value_char": "456",
                "field": self.env["ir.model.fields"]._get("res.partner", "name").id,
                "field_desc": "desc",
            }
        )
        self.assertEqual(r.old_value_formatted, "123")
        self.assertEqual(r.new_value_formatted, "456")

    def test_one2many_tracking_value(self):
        r = self.model.create(
            {
                "mail_message_id": self.msg.id,
                "field_type": "one2many",
                "old_value_char": "123",
                "new_value_char": "456",
                "field": self.env["ir.model.fields"]._get("res.partner", "name").id,
                "field_desc": "desc",
            }
        )
        self.assertEqual(r.old_value_formatted, "123")
        self.assertEqual(r.new_value_formatted, "456")

    def test_integer_tracking_value(self):
        r = self.model.create(
            {
                "mail_message_id": self.msg.id,
                "field_type": "integer",
                "old_value_integer": 1,
                "new_value_integer": 3,
                "field": self.env["ir.model.fields"]._get("res.partner", "name").id,
                "field_desc": "desc",
            }
        )
        self.assertEqual(r.old_value_formatted, str(1))
        self.assertEqual(r.new_value_formatted, str(3))

    def test_float_tracking_value(self):
        r = self.model.create(
            {
                "mail_message_id": self.msg.id,
                "field_type": "float",
                "old_value_float": 1.1,
                "new_value_float": 3.14159,
                "field": self.env["ir.model.fields"]._get("res.partner", "name").id,
                "field_desc": "desc",
            }
        )
        self.assertEqual(r.old_value_formatted, str(1.1))
        self.assertEqual(r.new_value_formatted, str(3.14159))

    def test_monetary_tracking_value(self):
        r = self.model.create(
            {
                "mail_message_id": self.msg.id,
                "field_type": "monetary",
                "old_value_monetary": 3.45,
                "new_value_monetary": 5.45,
                "field": self.env["ir.model.fields"]._get("res.partner", "name").id,
                "field_desc": "desc",
            }
        )
        self.assertEqual(r.old_value_formatted, str(3.45))
        self.assertEqual(r.new_value_formatted, str(5.45))

    def test_datetime_tracking_value(self):
        r = self.model.create(
            {
                "mail_message_id": self.msg.id,
                "field_type": "datetime",
                "old_value_datetime": "2018-01-01",
                "new_value_datetime": "2018-01-04",
                "field": self.env["ir.model.fields"]._get("res.partner", "name").id,
                "field_desc": "desc",
            }
        )
        self.assertEqual(r.old_value_formatted, "2018-01-01 00:00:00")
        self.assertEqual(r.new_value_formatted, "2018-01-04 00:00:00")

    def test_text_tracking_value(self):
        r = self.model.create(
            {
                "mail_message_id": self.msg.id,
                "field_type": "text",
                "old_value_text": "previous",
                "new_value_text": "next",
                "field": self.env["ir.model.fields"]._get("res.partner", "name").id,
                "field_desc": "desc",
            }
        )
        self.assertEqual(r.old_value_formatted, "previous")
        self.assertEqual(r.new_value_formatted, "next")
