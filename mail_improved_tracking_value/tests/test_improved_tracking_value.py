# Copyright 2018 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import json

from odoo import Command

from odoo.addons.base.tests.common import BaseCommon
from odoo.addons.mail.models.mail_track_mixin import MailTrackMixin


class TestImprovedTrackingValue(BaseCommon):
    """Direct calls of ``_create_mail_tracking_values`` on a real model."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.tag_a, cls.tag_b, cls.tag_c = cls.env["res.partner.category"].create(
            [{"name": "Tag A"}, {"name": "Tag B"}, {"name": "Tag C"}]
        )
        cls.child_a, cls.child_b = cls.env["res.partner"].create(
            [{"name": "Child A"}, {"name": "Child B"}]
        )
        cls.fields_info = cls.partner.fields_get(
            ["category_id", "child_ids", "name", "parent_id"]
        )

    def _track(self, initial_value, new_value, col_name, col_info=None):
        """Return the values with the module and the values Odoo computes."""
        col_info = col_info or self.fields_info[col_name]
        args = (initial_value, new_value, col_name, col_info)
        result = self.partner._create_mail_tracking_values(*args)
        # Odoo core implementation, without any override from this module
        core = MailTrackMixin._create_mail_tracking_values(self.partner, *args)
        return result, core

    def _assert_ids_added(self, result, core, old_ids, new_ids):
        """The module adds the JSON ids and leaves Odoo's values untouched."""
        self.assertEqual(result.get("old_value_text"), json.dumps(old_ids))
        self.assertEqual(result.get("new_value_text"), json.dumps(new_ids))
        self.assertEqual(
            result,
            dict(
                core,
                old_value_text=json.dumps(old_ids),
                new_value_text=json.dumps(new_ids),
            ),
        )

    def test_many2many_ids_both_sides(self):
        """Ids in recordset order, names computed by Odoo."""
        old = self.tag_b | self.tag_a
        new = self.tag_c | self.tag_a
        result, core = self._track(old, new, "category_id")
        self.assertEqual(result["old_value_char"], "Tag B, Tag A")
        self.assertEqual(result["new_value_char"], "Tag C, Tag A")
        self._assert_ids_added(
            result,
            core,
            [self.tag_b.id, self.tag_a.id],
            [self.tag_c.id, self.tag_a.id],
        )

    def test_many2many_empty_to_filled(self):
        """An empty recordset gives an empty JSON list."""
        empty = self.env["res.partner.category"]
        result, core = self._track(empty, self.tag_a, "category_id")
        self.assertEqual(result["old_value_char"], "")
        self.assertEqual(result.get("old_value_text"), "[]")
        self._assert_ids_added(result, core, [], [self.tag_a.id])

    def test_many2many_filled_to_empty(self):
        """A False value gives an empty JSON list."""
        result, core = self._track(self.tag_a | self.tag_b, False, "category_id")
        self.assertEqual(result["new_value_char"], "")
        self.assertEqual(result.get("new_value_text"), "[]")
        self._assert_ids_added(result, core, [self.tag_a.id, self.tag_b.id], [])

    def test_one2many_ids(self):
        """One2many behaves like many2many."""
        result, core = self._track(
            self.child_a, self.child_b | self.child_a, "child_ids"
        )
        self._assert_ids_added(
            result, core, [self.child_a.id], [self.child_b.id, self.child_a.id]
        )
        result, core = self._track(self.child_a, self.env["res.partner"], "child_ids")
        self._assert_ids_added(result, core, [self.child_a.id], [])

    def test_char_unchanged(self):
        """Non relational fields are left as Odoo computes them."""
        result, core = self._track("Old name", "New name", "name")
        self.assertEqual(result, core)
        self.assertNotIn("old_value_text", result)
        self.assertNotIn("new_value_text", result)

    def test_many2one_unchanged(self):
        """Many2one fields are left as Odoo computes them."""
        result, core = self._track(self.child_a, self.child_b, "parent_id")
        self.assertEqual(result, core)
        self.assertNotIn("old_value_text", result)
        self.assertNotIn("new_value_text", result)


class TestImprovedTrackingValueIntegration(BaseCommon):
    """A real write on tracked x2many fields."""

    model_name = "x_improved_tracking_test"

    @classmethod
    def default_env_context(cls):
        # BaseCommon disables tracking by default
        return {
            **super().default_env_context(),
            "tracking_disable": False,
            "mail_notrack": False,
        }

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.test_model = cls.env["ir.model"].create(
            {
                "name": "Improved Tracking Test Model",
                "model": cls.model_name,
                "is_mail_thread": True,
            }
        )
        cls.env["ir.model.fields"].create(
            {
                "name": "x_parent_id",
                "model_id": cls.test_model.id,
                "ttype": "many2one",
                "relation": cls.model_name,
            }
        )
        cls.tag_field, cls.child_field = cls.env["ir.model.fields"].create(
            [
                {
                    "name": "x_tag_ids",
                    "model_id": cls.test_model.id,
                    "ttype": "many2many",
                    "relation": "res.partner.category",
                    "relation_table": "x_improved_tracking_test_tag_rel",
                    "column1": "x_record_id",
                    "column2": "x_tag_id",
                    "tracking": True,
                },
                {
                    "name": "x_child_ids",
                    "model_id": cls.test_model.id,
                    "ttype": "one2many",
                    "relation": cls.model_name,
                    "relation_field": "x_parent_id",
                    "tracking": True,
                },
            ]
        )
        cls.tag_a, cls.tag_b = cls.env["res.partner.category"].create(
            [{"name": "Tag A"}, {"name": "Tag B"}]
        )

    def _flush_tracking(self):
        self.env.flush_all()
        self.env.cr.flush()

    def _read_tracking(self, record, field):
        return (
            self.env["mail.tracking.value"]
            .sudo()
            .search_read(
                [
                    ("field_id", "=", field.id),
                    ("mail_message_id.model", "=", record._name),
                    ("mail_message_id.res_id", "=", record.id),
                ],
                [
                    "old_value_char",
                    "new_value_char",
                    "old_value_text",
                    "new_value_text",
                ],
            )
        )

    def test_write_many2many_stores_ids(self):
        record = self.env[self.model_name].sudo().create({"x_name": "Record"})
        self._flush_tracking()
        record.write({"x_tag_ids": [Command.set(self.tag_a.ids)]})
        self._flush_tracking()
        record.write({"x_tag_ids": [Command.set((self.tag_a | self.tag_b).ids)]})
        self._flush_tracking()
        trackings = self._read_tracking(record, self.tag_field)
        self.assertEqual(len(trackings), 2)
        last, first = trackings  # mail.tracking.value is ordered by id DESC
        self.assertEqual(first["new_value_char"], "Tag A")
        self.assertEqual(first["old_value_text"], "[]")
        self.assertEqual(first["new_value_text"], json.dumps(self.tag_a.ids))
        self.assertEqual(last["old_value_text"], json.dumps(self.tag_a.ids))
        self.assertEqual(last["new_value_text"], json.dumps(record.x_tag_ids.ids))
        self.assertEqual(
            sorted(json.loads(last["new_value_text"])),
            sorted((self.tag_a | self.tag_b).ids),
        )

    def test_write_one2many_stores_ids(self):
        model = self.env[self.model_name].sudo()
        record = model.create({"x_name": "Parent"})
        child = model.create({"x_name": "Child"})
        self._flush_tracking()
        record.write({"x_child_ids": [Command.link(child.id)]})
        self._flush_tracking()
        trackings = self._read_tracking(record, self.child_field)
        self.assertEqual(len(trackings), 1)
        self.assertEqual(trackings[0]["new_value_char"], "Child")
        self.assertEqual(trackings[0]["old_value_text"], "[]")
        self.assertEqual(trackings[0]["new_value_text"], json.dumps(child.ids))
