# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.addons.social_media_base.hooks import remove_social_media


def uninstall_hook(env):
    """Remove the LinkedIn data when the connector is uninstalled."""
    remove_social_media(env, "linkedin")
