/** @odoo-module **/

import {SocialCommentDialog} from "@social_media_sync/components/social_comment_dialog/social_comment_dialog.esm";
import {patch} from "@web/core/utils/patch";

// The context key `social_media_x_sync` reads to answer the comments without
// asking X for the likes of the account.
const SKIP_LIKES_CONTEXT_X = "social_x_skip_likes";

patch(SocialCommentDialog.prototype, {
    /**
     * Refresh the comments of X without paying for the likes again.
     *
     * The likes are read once, when the dialog opens. The refresh of every
     * two minutes and the reload after an action ask for the comments
     * without them, and the comments already on screen keep the like they
     * hold; the new ones arrive without it.
     *
     * @override
     */
    async updateListComments() {
        if (this.props.media_type.raw_value !== "x") {
            return super.updateListComments();
        }
        const result = await this.env.services.orm.call(
            "social.post.account",
            "get_comments",
            [this.props.post.id.raw_value],
            {context: {[SKIP_LIKES_CONTEXT_X]: true}}
        );
        // A refresh that could not be read leaves the comments on screen.
        if (!result?.success) {
            return;
        }
        const likedByRef = new Map(
            this.state.comments.map((comment) => [comment.remote_ref, comment.liked])
        );
        this.setComments(
            (result.data || []).map((comment) =>
                likedByRef.has(comment.remote_ref)
                    ? {...comment, liked: likedByRef.get(comment.remote_ref)}
                    : comment
            )
        );
    },
});
