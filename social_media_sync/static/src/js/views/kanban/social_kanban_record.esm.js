/** @odoo-module **/

import {SocialCommentDialog} from "@social_media_sync/components/social_comment_dialog/social_comment_dialog.esm";
import {SocialKanbanRecord} from "@social_media_base/js/views/kanban/social_kanban_record.esm";
import {_t} from "@web/core/l10n/translation";
import {patch} from "@web/core/utils/patch";
import {useEffect} from "@odoo/owl";

/**
 * The card is patched instead of moved: it is one class that also draws the
 * images and the renderer is what registers it, so base has to keep owning
 * it. What comes back here is only what talks to the social media — reacting,
 * commenting, and checking the publication is still there.
 */
patch(SocialKanbanRecord.prototype, {
    /** @override */
    setup() {
        super.setup();
        // Which social media serve no reaction, read by the footer template
        // to hide the entry. A connector fills it in.
        this.record.notAvailableLike = [];

        useEffect(
            (value) => {
                if (value) {
                    const listener = this.onLikePost.bind(this);
                    value.addEventListener("click", listener);
                    return () => {
                        value.removeEventListener("click", listener);
                    };
                }
            },
            () => [this.rootRef.el.querySelector(".social-like-post")]
        );

        useEffect(
            (value) => {
                if (value) {
                    const listener = this.onPostComment.bind(this);
                    value.addEventListener("click", listener);
                    return () => {
                        value.removeEventListener("click", listener);
                    };
                }
            },
            () => [this.rootRef.el.querySelector(".social-post-comment")]
        );
    },

    onPostComment(ev) {
        ev.stopPropagation();
        this.dialogService.add(SocialCommentDialog, {
            title: _t("Comments"),
            account: this.record.account_id,
            post: this.record,
            media_type: this.record.media_type,
            images: JSON.parse(this.record.image_urls.raw_value),
        });
    },

    /**
     * Ask the server whether the publication is still on the social media.
     * The check lives in Python so this card and the form button answer the
     * same thing.
     *
     * @override
     * @returns {Promise<Boolean>}
     */
    async validPostExist() {
        const postAccountId = this.record.id.raw_value;
        if (!postAccountId) {
            return false;
        }
        return await this.orm.call("social.post.account", "check_post_exists", [
            postAccountId,
        ]);
    },
});
