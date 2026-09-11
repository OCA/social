# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.fields import Command

from .test_social_common import TestSocialMediaBaseCommon

MENU_XML_IDS = (
    "social_root_menu",
    "social_dashboard_menu",
    "social_statistics_menu",
    "social_post_menu",
    "utm_campaign_menu",
    "social_configuration_menu",
    "social_account_menu",
    "social_media_menu",
)


class TestSocialMenusBase(TestSocialMediaBaseCommon):
    """Who the menu of the application is drawn for.

    The group is declared on the root alone, and what the client loads starts
    from the roots it can see, so the children follow their parent.
    """

    def _user(self, login, social=False):
        groups = [self.env.ref("base.group_user").id]
        if social:
            groups.append(self.env.ref("social_media_base.group_social_media_user").id)
        return self.env["res.users"].create(
            {
                "login": login,
                "name": login,
                "groups_id": [Command.set(groups)],
            }
        )

    def _menus(self):
        """The eight entries, with the children as a fresh install leaves them.

        Removing ``groups`` from a ``menuitem`` does not clear the field on a
        database that already carries it, so the children are put back to what
        the XML declares before asserting who sees them.
        """
        menus = self.env["ir.ui.menu"].browse()
        for xml_id in MENU_XML_IDS:
            menus |= self.env.ref(f"social_media_base.{xml_id}")
        root = self.env.ref("social_media_base.social_root_menu")
        (menus - root).groups_id = [Command.clear()]
        return menus

    def _loaded_menu_ids(self, user):
        menus = self.env["ir.ui.menu"].with_user(user).load_menus(False)
        return {menu_id for menu_id in menus if isinstance(menu_id, int)}

    def test_the_menu_needs_the_group(self):
        """None of the eight entries reaches a user outside the group.

        The group of the root is what decides it: what the client loads starts
        from the roots the user can see.
        """
        menus = self._menus()
        loaded = self._loaded_menu_ids(self._user("social_outsider"))
        for menu in menus:
            self.assertNotIn(menu.id, loaded, menu.complete_name)

    def test_the_group_draws_the_whole_menu(self):
        """A user of the group gets the root and every entry under it."""
        menus = self._menus()
        loaded = self._loaded_menu_ids(self._user("social_insider", social=True))
        for menu in menus:
            self.assertIn(menu.id, loaded, menu.complete_name)
