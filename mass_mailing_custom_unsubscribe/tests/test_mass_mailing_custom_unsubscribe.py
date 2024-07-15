# Copyright 2024 Tecnativa - David Vidal
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo.tests import tagged

from odoo.addons.mass_mailing.tests.test_mailing_controllers import (
    TestMailingControllers,
)


@tagged("mailing_portal", "post_install", "-at_install")
class TestMailingControllersCustomUnsubscribe(TestMailingControllers):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def test_mailing_unsubscribe_from_document_tour(self):
        # pylint: disable=missing-return
        super().test_mailing_unsubscribe_from_document_tour()
        # unsubscription = self.env["mail.unsubscription"].search(
        #     [], limit=1, order="id desc"
        # )
        # self.assertEqual(unsubscription.email, 'fleurus@example.com')
        # self.assertEqual(unsubscription.action, 'blacklist_add')

    def test_mailing_unsubscribe_from_document_tour_mailing_user(self):
        # pylint: disable=missing-return
        super().test_mailing_unsubscribe_from_document_tour_mailing_user()

    def test_mailing_unsubscribe_from_list_tour(self):
        # pylint: disable=missing-return
        super().test_mailing_unsubscribe_from_list_tour()

    def test_mailing_unsubscribe_from_list_with_update_tour(self):
        pass
        # super().test_mailing_unsubscribe_from_list_with_update_tour()

    def test_mailing_unsubscribe_from_my(self):
        pass
        # super().test_mailing_unsubscribe_from_my()

    def test_mailing_view(self):
        # Not needed
        pass
