# Copyright 2025 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from . import controllers
from . import models
from . import wizards


def remove_social_media(env, media_type):
    """Remove the data of a social media, called from a connector ``uninstall_hook``."""
    env["social.account"]._remove_social_media(media_type)
