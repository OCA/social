# Copyright 2022 Foodles (http://www.foodles.co).
# @author Pierre Verkest <pierreverkest84@gmail.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.exceptions import ValidationError
from odoo.tests.common import Form, SavepointCase

from odoo.addons.mail.tests.common import MockEmail


class TestTemplateAttachExistingAttachment(SavepointCase, MockEmail):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.template = cls.env.ref("mail.email_template_partner")
        cls.template.subject = "TEST"
        cls.partner_01 = cls.env["res.partner"].create(
            {
                "name": "Partner 1",
                "email": "partner1@example.org",
            }
        )
        cls.partner_02 = cls.env["res.partner"].create(
            {
                "name": "Partner 2",
                "email": "partner2@example.org",
            }
        )
        cls.partner_03_no_attachment = cls.env["res.partner"].create(
            {
                "name": "Partner 3 without attachment",
                "email": "partner3@example.org",
            }
        )
        cls.attach_p1_csv1 = cls.env["ir.attachment"].create(
            {
                "name": "attach1.csv",
                "datas": "bWlncmF0aW9uIHRlc3Q=",
                "res_model": "res.partner",
                "res_id": cls.partner_01.id,
            }
        )
        cls.attach_p1_jpg = cls.env["ir.attachment"].create(
            {
                "name": "attach.jpg",
                "datas": "bWlncmF0aW9uIHRlc3Q=",
                "res_model": "res.partner",
                "res_id": cls.partner_01.id,
            }
        )
        cls.attach_p1_csv2 = cls.env["ir.attachment"].create(
            {
                "name": "attach2.csv",
                "datas": "bWlncmF0aW9uIHRlc3Q=",
                "res_model": "res.partner",
                "res_id": cls.partner_01.id,
            }
        )
        cls.attach_p1_png = cls.env["ir.attachment"].create(
            {
                "name": "attach.png",
                "datas": "bWlncmF0aW9uIHRlc3Q=",
                "res_model": "res.partner",
                "res_id": cls.partner_01.id,
            }
        )
        cls.attach_p2_csv = cls.env["ir.attachment"].create(
            {
                "name": "attach.csv",
                "datas": "bWlncmF0aW9uIHRlc3Q=",
                "res_model": "res.partner",
                "res_id": cls.partner_02.id,
            }
        )
        cls.attach_p2_png = cls.env["ir.attachment"].create(
            {
                "name": "attach.png",
                "datas": "bWlncmF0aW9uIHRlc3Q=",
                "res_model": "res.partner",
                "res_id": cls.partner_02.id,
            }
        )

    def _get_composer_context(self, records, mass_mail=False, overwrite=None):
        """Inspired from
        addons.test_mail.tests.test_mail_composer:TestMailComposer._get_web_context
        """
        if not overwrite:
            overwrite = {}
        ctx = dict(
            default_model=records._name,
            active_model=records._name,
            active_id=records[0].id,
            default_composition_mode="mass_mail" if mass_mail else "comment",
            mail_auto_delete=False,
            default_template_id=self.template.id,
        )
        if mass_mail:
            ctx["active_ids"] = records.ids
        else:
            ctx["default_res_id"] = self.partner_01.id
        ctx.update(overwrite)
        return ctx

    def test_wrong_pattern_raises(self):
        with self.assertRaisesRegex(
            ValidationError,
            r"The following regular expression is invalid to select attachment: *",
        ):
            self.template.attach_exist_document_regex = "*"

    def test_default_images_attachments_from_template(self):
        self.template.attach_exist_document_regex = ".*.[png|jpg]"
        with Form(
            self.env["mail.compose.message"].with_context(
                **self._get_composer_context(
                    self.partner_01, overwrite={"default_template_id": None}
                )
            )
        ) as composer:
            self.assertEqual(len(composer.object_attachment_ids), 0)
            composer.template_id = self.template
            self.assertEqual(len(composer.object_attachment_ids), 2)
            composed_mail = composer.save()
        self.assertEqual(
            composed_mail.object_attachment_ids,
            (self.attach_p1_jpg | self.attach_p1_png),
        )

    def test_clear_default_images_attachments_changing_template(self):
        self.template.attach_exist_document_regex = ".*.[png|jpg]"
        with Form(
            self.env["mail.compose.message"].with_context(
                **self._get_composer_context(self.partner_01)
            )
        ) as composer:
            self.assertEqual(len(composer.object_attachment_ids), 2)
            composer.template_id = self.env["mail.template"].browse()
            self.assertEqual(len(composer.object_attachment_ids), 0)

    def test_send_email_with_default_and_manual_extra_attachment(self):
        self.template.attach_exist_document_regex = ".*.[png|jpg]"
        with Form(
            self.env["mail.compose.message"].with_context(
                **self._get_composer_context(self.partner_01)
            )
        ) as composer:
            composer.object_attachment_ids.add(self.attach_p1_csv1)
            self.assertEqual(len(composer.object_attachment_ids), 3)
            composed_mail = composer.save()

        self.assertEqual(len(composed_mail.object_attachment_ids), 3)
        self.assertEqual(
            composed_mail.object_attachment_ids,
            (self.attach_p1_png | self.attach_p1_jpg | self.attach_p1_csv1),
        )

        with self.mock_mail_gateway():
            composed_mail.send_mail()

        self.assertEqual(
            self.partner_01.message_ids[0].attachment_ids,
            (self.attach_p1_png | self.attach_p1_jpg | self.attach_p1_csv1),
        )

    def test_no_pattern(self):
        self.template.attach_exist_document_regex = False
        with Form(
            self.env["mail.compose.message"].with_context(
                **self._get_composer_context(self.partner_01)
            )
        ) as composer:
            self.assertEqual(len(composer.object_attachment_ids), 0)
            composed_mail = composer.save()
        self.assertEqual(len(composed_mail.object_attachment_ids), 0)

    def test_send_mass_mail_with_default_extra_attachment(self):
        self.template.attach_exist_document_regex = ".*.csv"
        records = self.partner_01 | self.partner_02 | self.partner_03_no_attachment
        composed_mail = Form(
            self.env["mail.compose.message"].with_context(
                **self._get_composer_context(records, mass_mail=True)
            )
        ).save()

        with self.mock_mail_gateway():
            composed_mail.send_mail()

        self.assertEqual(
            self.partner_01.message_ids[0].attachment_ids,
            (self.attach_p1_csv1 | self.attach_p1_csv2),
        )
        self.assertEqual(
            self.partner_02.message_ids[0].attachment_ids, (self.attach_p2_csv)
        )
        self.assertEqual(
            len(self.partner_03_no_attachment.message_ids[0].attachment_ids), 0
        )

    def test_mass_mailing_no_pattern(self):
        self.template.attach_exist_document_regex = False
        records = self.partner_01 | self.partner_02 | self.partner_03_no_attachment
        composed_mail = Form(
            self.env["mail.compose.message"].with_context(
                **self._get_composer_context(records, mass_mail=True)
            )
        ).save()
        self.assertEqual(len(composed_mail.object_attachment_ids), 0)

        with self.mock_mail_gateway():
            composed_mail.send_mail()

        self.assertEqual(len(self.partner_01.message_ids[0].attachment_ids), 0)
        self.assertEqual(len(self.partner_02.message_ids[0].attachment_ids), 0)
        self.assertEqual(
            len(self.partner_03_no_attachment.message_ids[0].attachment_ids), 0
        )

    def test_switch_template_with_different_templates(self):

        jpg_template = self.template
        png_template = self.template.copy()
        jpg_template.attach_exist_document_regex = ".*.jpg"
        png_template.attach_exist_document_regex = ".*.png"
        with Form(
            self.env["mail.compose.message"].with_context(
                **self._get_composer_context(
                    self.partner_01, overwrite={"default_template_id": None}
                )
            )
        ) as composer:
            self.assertEqual(len(composer.object_attachment_ids), 0)
            composer.template_id = jpg_template
            self.assertEqual(len(composer.object_attachment_ids), 1)
            composed_mail = composer.save()
            self.assertEqual(
                composed_mail.object_attachment_ids,
                self.attach_p1_jpg,
            )
            composer.template_id = png_template
            composed_mail = composer.save()
            self.assertEqual(len(composer.object_attachment_ids), 1)
            self.assertEqual(
                composed_mail.object_attachment_ids,
                self.attach_p1_png,
            )
