# Copyright 2026 Domatix <https://www.domatix.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from . import controllers, models, wizards


def uninstall_hook(env):
    env["social.account"]._remove_social_media("tiktok")
