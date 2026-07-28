# Copyright 2025 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from . import controllers
from . import models
from . import wizards

from odoo.addons.social_media_base import remove_social_media


def uninstall_hook(env):
    remove_social_media(env, "linkedin")
