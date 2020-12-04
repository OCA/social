# Copyright 2016 ACSONE SA/NV (<http://acsone.eu>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo.tests import common


class TestMailAutoSubscribe(common.TransactionCase):
    def setUp(self):
        super(TestMailAutoSubscribe, self).setUp()
        self.company_1 = self.env["res.partner"].create(
            {
                "name": "Company 1",
                "email": "partnercompany@example.org",
                "is_company": True,
                "parent_id": False,
            }
        )
        self.company_2 = self.env["res.partner"].create(
            {
                "name": "Company 2",
                "email": "partnercompany@example.org",
                "is_company": True,
                "parent_id": False,
            }
        )
        self.company_3 = self.env["res.partner"].create(
            {
                "name": "Company 3",
                "email": "partnercompany@example.org",
                "is_company": True,
                "parent_id": False,
            }
        )
        self.auto_subscribe_tag = self.env["res.partner.category"].create(
            {
                "name": "Contacts",
                "auto_subscribe": True,
                "model_ids": [(6, 0, [self.env.ref("base.model_res_partner").id])],
            }
        )
        self.normal_tag = self.env["res.partner.category"].create(
            {"name": "Client", "auto_subscribe": False}
        )
        self.partner_1 = self.env["res.partner"].create(
            {
                "name": "Partner 1",
                "email": "subscribe_child@example.org",
                "is_company": False,
                "parent_id": self.company_1.id,
                "category_id": [(4, self.auto_subscribe_tag.id)],
            }
        )
        self.partner_2 = self.env["res.partner"].create(
            {
                "name": "Partner 2",
                "email": "subscribe_child@example.org",
                "is_company": False,
                "parent_id": self.company_1.id,
                "category_id": [(4, self.auto_subscribe_tag.id)],
            }
        )
        self.partner_3 = self.env["res.partner"].create(
            {
                "name": "Partner 3",
                "email": "subscribe_child@example.org",
                "is_company": False,
                "parent_id": self.company_1.id,
            }
        )

    def test_subscriptions(self):
        self.mail_wizard_invite_1 = self.env["mail.wizard.invite"].create(
            {
                "partner_ids": self.partner_1,
                "send_mail": False,
                "res_id": self.company_2.id,
                "res_model": "res.partner",
            }
        )
        self.mail_wizard_invite_3 = self.env["mail.wizard.invite"].create(
            {
                "partner_ids": self.partner_3,
                "send_mail": False,
                "res_id": self.company_3.id,
                "res_model": "res.partner",
            }
        )
        self.mail_wizard_invite_1.add_followers()
        self.mail_wizard_invite_3.add_followers()
        self.assertTrue(
            self.partner_1.id in self.company_2.message_follower_ids.partner_id.ids
        )
        self.assertTrue(
            self.partner_2.id in self.company_2.message_follower_ids.partner_id.ids
        )
        self.assertTrue(
            self.partner_1.id in self.company_3.message_follower_ids.partner_id.ids
        )
        self.assertTrue(
            self.partner_2.id in self.company_3.message_follower_ids.partner_id.ids
        )
        self.assertFalse(
            self.partner_3.id in self.company_2.message_follower_ids.partner_id.ids
        )

    def test_tag_name(self):
        self.assertTrue(
            self.auto_subscribe_tag.display_name == "Contacts - \u24B6\u24C8"
        )
        self.assertTrue(self.normal_tag.display_name == "Client")
