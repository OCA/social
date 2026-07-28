# Copyright 2025 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from . import models

POST_ACTION_VIEW_MODE = "kanban,tree,form"


def uninstall_hook(env):
    """Drop the calendar mode from the posts action.

    The action belongs to ``social_media_base``, so uninstalling this module
    does not revert the ``view_mode`` written by its data file and the action
    would keep announcing a calendar view that no longer exists.
    """
    action = env.ref("social_media_base.social_post_action", raise_if_not_found=False)
    if action and "calendar" in action.view_mode:
        action.view_mode = POST_ACTION_VIEW_MODE
