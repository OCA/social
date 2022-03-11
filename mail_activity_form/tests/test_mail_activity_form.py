# Copyright 2021 Hunki Enterprises BV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import exceptions
from odoo.tests.common import TransactionCase


class TestMailActivityForm(TransactionCase):
    def setUp(self):
        super().setUp()
        self.activity_type = self.env.ref("mail_activity_form.demo_type1")
        self.partner = self.env["res.partner"].search([], limit=1)

    def _create_activity(self, note, activity_type_id=None):
        """ Create an activity with some default values """
        return (
            self.env["mail.activity"]
            .with_context(
                default_res_model=self.partner._name,
                default_res_id=self.partner.id,
                default_activity_type_id=activity_type_id or self.activity_type.id,
            )
            .create({"note": note})
        )

    def test_evaluation(self):
        """ Test that expressions evaluate correctly """
        cell_template = (
            '<td %(p)sid="%%s" %(p)stype="float" %(p)seditable="1">%%s</td>'
        ) % {"p": self.env["mail.activity"]._mail_activity_form_prefix}
        activity = self._create_activity(
            self.activity_type.default_description.replace(
                cell_template % ("value1", ""), cell_template % ("value1", "1"),
            ).replace(cell_template % ("value2", ""), cell_template % ("value2", "2"),),
        )
        result_string = (
            'compute="(value1 + value2 + object[-1:].id) * factor">%s</td>'
        ) % str(float(1 + 2 + self.partner.id) * 42)
        self.assertIn(result_string, activity.note)

    def test_editable(self):
        """ Test we're only allowed to edit editable nodes """

        activity = self._create_activity("<div/>")

        with self.assertRaises(exceptions.UserError):
            activity.note = "<div></div><table></table>"
        with self.assertRaises(exceptions.UserError):
            activity.note = "<span />"
        with self.assertRaises(exceptions.UserError):
            activity.note = "<div id='different' /><table/>"
        with self.assertRaises(exceptions.UserError):
            self._create_activity(
                self.activity_type.default_description.replace(
                    "Value1:", "some other text",
                )
            )
        with self.assertRaises(exceptions.UserError):
            self._create_activity(
                self.activity_type.default_description.replace(
                    'compute="(value1 + value2 + object[-1:].id) * factor"',
                    'compute="different"',
                )
            )

    def test_change_template(self):
        """
        Test that after changing a template, we get the updated version when reading
        """
        cell_template = (
            '<td %(p)sid="%%s" %(p)stype="float" %(p)seditable="1">%%s</td>'
        ) % {"p": self.env["mail.activity"]._mail_activity_form_prefix}
        activity = self._create_activity(
            self.activity_type.default_description.replace(
                cell_template % ("value1", ""), cell_template % ("value1", "1"),
            ).replace(cell_template % ("value2", ""), cell_template % ("value2", "2"),),
        )
        extra_node = "<div>some extra text</div>"
        self.activity_type.default_description += extra_node
        updated_note = activity.read(["note"])[0]["note"]
        self.assertIn(extra_node, updated_note)
        self.assertIn(cell_template % ("value1", "1.0"), updated_note)
        self.assertIn(cell_template % ("value2", "2.0"), updated_note)
