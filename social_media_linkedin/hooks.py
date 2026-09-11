# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).


def uninstall_hook(env):
    """Remove the LinkedIn data when the connector is uninstalled."""
    env["social.account"]._remove_social_media("linkedin")
