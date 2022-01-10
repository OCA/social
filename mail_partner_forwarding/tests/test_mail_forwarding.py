# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo_test_helper import FakeModelLoader

from odoo import _
from odoo.tests.common import SavepointCase, tagged


@tagged("post_install", "-at_install")
class TestMailForwarding(SavepointCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Setup env
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        # Load fake order model
        cls.loader = FakeModelLoader(cls.env, cls.__module__)
        cls.loader.backup_registry()
        from .models.fake_order import FakeOrder

        cls.loader.update_registry((FakeOrder,))
        cls.fake_order_model = cls.env["ir.model"].search(
            [("model", "=", "fake.order")]
        )
        # Partner To forward
        cls.partner_1 = cls.env.ref("base.user_demo").partner_id
        cls.partner_2 = cls.env.ref("base.user_admin").partner_id

        # Configurate in the user setting the user to be forwarding
        cls.partner_2.forwarding_partner_id = cls.partner_1
        # Empty fake.order
        cls.order = cls.env["fake.order"].create({"partner_id": cls.partner_2.id})

    @classmethod
    def tearDownClass(cls):
        cls.loader.restore_registry()
        return super().tearDownClass()

    def test_message_post_forwarding(self):
        """Test forwarding when send a message for the user"""
        self.order.message_post(
            body=_("Test"),
            message_type="comment",
            subtype="mail.mt_comment",
            partner_ids=[self.partner_2.id],
        )
