# Copyright 2026 Tecnativa - Carlos Lopez
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests import new_test_user

from odoo.addons.base.tests.common import BaseCommon


class TestResPartnerSearchForChannelInvite(BaseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.gateway_user = new_test_user(
            cls.env,
            login="test_gateway_user",
            groups="base.group_user,mail_gateway.gateway_user",
            name="Test Gateway Agent",
        )
        cls.regular_user = new_test_user(
            cls.env,
            login="test_regular_user",
            groups="base.group_user",
            name="Test Regular Agent",
        )
        cls.gateway_channel = cls.env["discuss.channel"].create(
            {"name": "Gateway Channel", "channel_type": "gateway"}
        )
        cls.regular_channel = cls.env["discuss.channel"].create(
            {"name": "Regular Channel", "channel_type": "channel"}
        )

    def test_only_gateway_users_are_suggested_on_gateway_channels(self):
        result = self.env["res.partner"].search_for_channel_invite(
            "Test", channel_id=self.gateway_channel.id
        )
        suggested_ids = {p["id"] for p in result["data"].get("res.partner", [])}
        self.assertIn(self.gateway_user.partner_id.id, suggested_ids)
        self.assertNotIn(self.regular_user.partner_id.id, suggested_ids)

    def test_regular_channels_are_not_restricted(self):
        result = self.env["res.partner"].search_for_channel_invite(
            "Test", channel_id=self.regular_channel.id
        )
        suggested_ids = {p["id"] for p in result["data"].get("res.partner", [])}
        self.assertIn(self.gateway_user.partner_id.id, suggested_ids)
        self.assertIn(self.regular_user.partner_id.id, suggested_ids)
