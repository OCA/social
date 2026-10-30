/** @odoo-module **/

import {SocialComment} from "@social_media_sync/components/social_comment/social_comment.esm";
import {patch} from "@web/core/utils/patch";

patch(SocialComment.prototype, {
    /**
     * The patch is applied to the prototype, so it answers for every media,
     * and every entry point checks the media before acting.
     *
     * @override
     */
    canLikeComment() {
        if (this._isXComment()) {
            return true;
        }
        return super.canLikeComment();
    },

    /**
     * X only deletes the tweets of the account that asks, so the entry is
     * offered on the comments the account wrote and on no other.
     *
     * @override
     */
    canDeleteComment() {
        if (this._isXComment()) {
            return (
                Boolean(this.props.socialComment.author_ref) &&
                this.props.socialComment.author_ref ===
                    this.props.post.account_remote_ref.raw_value
            );
        }
        return super.canDeleteComment();
    },

    /** @override */
    async _onDeleteComment() {
        if (!this._isXComment()) {
            return super._onDeleteComment();
        }
        return this.socialService.deleteComment(
            this.props.post.id.raw_value,
            this.props.socialComment.remote_ref
        );
    },

    /**
     * Keep the answer of X on the comment the dialog holds, too.
     *
     * The refresh of the dialog asks for the comments without their likes,
     * and keeps the like of those it already holds. Writing it there is what
     * makes a like given from here survive that refresh, and a branch folded
     * and unfolded again, which draws its comments anew from that list.
     *
     * @override
     */
    async onLikeComment() {
        await super.onLikeComment();
        if (this._isXComment()) {
            this.props.socialComment.liked = this.state.liked;
        }
    },

    _isXComment() {
        return this.props.post.media_type.raw_value === "x";
    },
});
