/** @odoo-module **/

import {SocialKanbanModel} from "@social_media_base/js/views/kanban/social_kanban_model.esm";
import {_t} from "@web/core/l10n/translation";
import {patch} from "@web/core/utils/patch";

patch(SocialKanbanModel.prototype, {
    /**
     * Answer a Recommend that no bridge can serve.
     *
     * The *Recommend* entry is drawn by this module, and a social media whose
     * bridge sends no reaction is told apart from one that has none: the
     * connectors that do have a server side patch this method and answer for
     * their own media, and the ones that do not keep this answer, so the card
     * says plainly why nothing happens instead of doing nothing.
     *
     * @param {Object} record the publication the Recommend was asked on.
     * @returns {Object} `success`, `message`, `post_deleted` and `liked`.
     */
    onLikePost(record) {
        if (!record) {
            return {success: false, message: "", post_deleted: false, liked: false};
        }
        return {
            success: false,
            message: _t("Likes are not available for this social media."),
            post_deleted: false,
            liked: false,
        };
    },

    /**
     * Withdraw a Recommend that no bridge can serve.
     *
     * The counterpart of `onLikePost`, and it answers the same way and for
     * the same reason: without a bridge there is no server side to withdraw
     * the reaction from.
     *
     * @param {Object} record the publication the Recommend was withdrawn on.
     * @returns {Object} `success`, `message`, `post_deleted` and `liked`.
     */
    onUnlikePost(record) {
        return this.onLikePost(record);
    },

    /**
     * The same button, which now also imports the publications.
     *
     * The answer stays the one base defines — whether anything was refreshed
     * — because it is what the notification is written from; the imported
     * records reach the cards through the reload the controller does anyway.
     *
     * What the import answered is kept aside instead of thrown away: an empty
     * answer is the server saying that no account needed importing, which is
     * neither of the two cases base knows how to word.
     *
     * @override
     */
    async onUpdatePostsAndStatistics(accountId = null, postId = null) {
        const refreshed = await super.onUpdatePostsAndStatistics(accountId);
        const account = accountId ? [accountId] : [];
        const imported = await this.orm.silent.call(
            "social.account",
            "update_posts_statistics",
            [account, postId, this._getDomainSocialAccount()]
        );
        this.postsImported = Boolean((imported || []).length);
        return refreshed;
    },

    /**
     * The two flags the card reads to announce what this module imports: the
     * import running in the background and the publications waiting for one.
     * Base asks for neither, because base has neither.
     *
     * @override
     */
    _accountFields() {
        return [...super._accountFields(), "pending_initial_sync", "posts_need_import"];
    },
});
