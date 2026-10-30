# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging

from odoo import _

_logger = logging.getLogger(__name__)


def post_init_hook(env):
    """Tell the LinkedIn accounts that their token knows nothing of the Ads API.

    An access token keeps the scopes it was issued with, so every account
    associated before this module was installed reaches the Ads API without
    ``r_ads`` and LinkedIn refuses the call. Nothing can be fixed from here:
    only a new authorization brings the scopes, and it needs the Advertising
    API product on the LinkedIn application first. The accounts are posted
    the instructions instead, on their own chatter, so the message is waiting
    for whoever opens them.
    """
    accounts = env["social.account"].search([("media_id.media_type", "=", "linkedin")])
    concerned = accounts.filtered(lambda account: account.linkedin_missing_ads_scopes)
    if not concerned:
        return
    _logger.info(
        "%d LinkedIn account(s) have to be authorized again for the Ads API",
        len(concerned),
    )
    for account in concerned:
        account.message_post(
            body=_(
                "The Advertising module for LinkedIn was installed. The token "
                "of this account was not granted %(scopes)s, so LinkedIn "
                "refuses the advertising calls. Add the Advertising API "
                "product to the LinkedIn application, then press Update "
                "account with Update keys checked to authorize this account "
                "again: refreshing the token alone keeps the scopes it "
                "already has.",
                scopes=account.linkedin_missing_ads_scopes,
            )
        )
