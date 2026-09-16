# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.addons.social_media_x.tests.test_common_x import TestSocialCommonX

PATCH_X_SYNC_MODELS = "odoo.addons.social_media_x_sync.models"
PATCH_ACCOUNT_X_SYNC = "{}.social_account.SocialAccount.{}".format(
    PATCH_X_SYNC_MODELS, "{}"
)
PATCH_POST_ACCOUNT_X_SYNC = "{}.social_post_account.SocialPostAccount.{}".format(
    PATCH_X_SYNC_MODELS, "{}"
)
LOGGER_ACCOUNT_X_SYNC = f"{PATCH_X_SYNC_MODELS}.social_account"
LOGGER_POST_ACCOUNT_X_SYNC = f"{PATCH_X_SYNC_MODELS}.social_post_account"


class TestSocialSyncCommonX(TestSocialCommonX):
    """The fixtures of the connector are enough to synchronize X.

    They are the same records — the media, the account, the post and its
    publication; what changes is which module holds the code under test.
    Subclassed instead of moved so the connector keeps a suite of its own that
    runs without this bridge installed.
    """

    @staticmethod
    def _count_search_calls(mock_search, model=None, domain_leaf=None):
        """Count patched ``search`` calls narrowed to a model and/or domain leaf.

        Every social connector extends ``social.account``, so the ``super()``
        chain of an X method also runs the code of any other installed
        connector. A raw ``call_count`` would therefore depend on which
        modules happen to be installed.

        :param mock_search: mock of ``BaseModel.search`` patched with
            ``autospec=True``, so ``self`` is the first positional argument.
        :param model: only count calls made on this model name.
        :param domain_leaf: only count calls whose domain contains this leaf.
        :rtype: int
        """
        count = 0
        for call in mock_search.call_args_list:
            records = call.args[0]
            domain = (
                call.args[1] if len(call.args) > 1 else call.kwargs.get("domain")
            ) or []
            if model and records._name != model:
                continue
            if domain_leaf and domain_leaf not in domain:
                continue
            count += 1
        return count

    def get_search_side_effect_x(self):
        """Return a ``search`` side effect answering X domains only.

        Other installed connectors search ``social.account`` on the same
        ``super()`` chain; they must get an empty recordset instead of the X
        accounts of this test.
        """

        def side_effect(records, domain=None, *args, **kwargs):
            if records._name == "social.post.account":
                return self.SocialPostAccountX
            if ("media_type", "=", "x") in (domain or []):
                return self.SocialAccountX
            return records.browse()

        return side_effect
