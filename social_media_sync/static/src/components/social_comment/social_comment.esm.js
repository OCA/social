/** @odoo-module **/

import {Component, useState} from "@odoo/owl";
import {ConfirmationDialog} from "@web/core/confirmation_dialog/confirmation_dialog";
import {Dropdown} from "@web/core/dropdown/dropdown";
import {DropdownItem} from "@web/core/dropdown/dropdown_item";
import {_t} from "@web/core/l10n/translation";
import {useService} from "@web/core/utils/hooks";

export class SocialComment extends Component {
    static template = "social_media_base.SocialComment";
    static components = {
        Dropdown,
        DropdownItem,
    };
    static props = {
        socialComment: {type: Object, required: true},
        post: {type: Object, required: true},
        // The replies already known, the ones the social media served
        // together with the comments instead of apart.
        replies: {type: Array, optional: true},
        isReply: {type: Boolean, optional: true},
    };
    static defaultProps = {
        replies: [],
        isReply: false,
    };

    setup() {
        super.setup();
        this.socialService = useService("social_service");
        this.notificationService = useService("notification");
        this.effectService = useService("effect");
        this.dialog = useService("dialog");
        // The aim of the composer is shared state, and the button has to
        // redraw when another comment steals it.
        this.socialState = useState(this.socialService.state);
        this.state = useState({
            expanded: false,
            loading: false,
            replies: [],
            // What the social media said without being asked. LinkedIn says
            // nothing until the replies are read, and answers `null` here.
            count: this.props.socialComment.reply_count ?? null,
        });
    }

    /**
     * The name to show for whoever wrote the comment.
     *
     * What the social media puts in `actor` is not the same everywhere: X
     * answers a name, LinkedIn a URN — and, when the comment carries no
     * `lastModified`, a dict. Anything that is not a readable name falls back
     * to the author of the publication, which is what was shown before.
     *
     * @returns {String} The name to draw in the header.
     */
    get authorName() {
        const actor = this.props.socialComment.actor;
        if (typeof actor === "string" && actor && !actor.startsWith("urn:")) {
            return actor;
        }
        return this.props.post.author.raw_value;
    }

    /**
     * @returns {String} The avatar of the comment, or the one of the account.
     */
    get authorAvatarUrl() {
        return (
            this.props.socialComment.author_image ||
            `/web/image/social.account/${this.props.post.account_id.raw_value}/image_128`
        );
    }

    get isReplyTarget() {
        return (
            this.socialState.replyTarget?.commentRef ===
            this.props.socialComment.remote_ref
        );
    }

    get replies() {
        return this.props.replies.length ? this.props.replies : this.state.replies;
    }

    get repliesCount() {
        return this.state.count ?? this.replies.length;
    }

    /**
     * Whether the comment offers to unfold its replies.
     *
     * A social media that counts them says so before being asked, and a
     * comment with none does not offer anything to unfold. The one that does
     * not count them, LinkedIn, always offers: the only way to know is to
     * ask, and that is what unfolding does.
     */
    get canExpandReplies() {
        if (this.props.isReply) {
            return false;
        }
        const count = this.props.socialComment.reply_count;
        return count === null || count === undefined || count > 0;
    }

    async onToggleReplies() {
        if (this.state.expanded) {
            this.state.expanded = false;
            return;
        }
        // The whole thread may have arrived with the comments, and then there
        // is nothing to ask for.
        if (this.props.replies.length) {
            this.state.expanded = true;
            return;
        }
        this.state.loading = true;
        const result = await this.socialService.getCommentReplies(
            this.props.post.id.raw_value,
            this.props.socialComment.remote_ref
        );
        this.state.loading = false;
        if (!result || !result.success) {
            // The message comes from the social media, it is not a literal
            // the translation extractor can collect.
            this.notificationService.add(
                (result && result.message) || _t("Error retrieving replies"),
                {type: "danger"}
            );
            return;
        }
        this.state.replies = result.data || [];
        this.state.count = result.count ?? this.state.replies.length;
        this.state.expanded = true;
    }

    /**
     * Whether the media behind this comment implements the deletion.
     *
     * `_onDeleteComment` is an empty hook here, so a connector that does not
     * override it would answer nothing and `deleteComment` would report a
     * failure for a call that never left the client. A connector that deletes
     * says so by overriding this, and only then is the entry offered.
     *
     * @returns {Boolean} Whether the comment can be deleted from here.
     */
    canDeleteComment() {
        return false;
    }

    async _onDeleteComment() {
        return {};
    }

    async onDeleteComment() {
        this.dialog.add(ConfirmationDialog, {
            title: _t("Delete comment"),
            body: _t("Are you sure you want to delete this comment?"),
            confirm: () => this.deleteComment(),
            confirmLabel: _t("Delete"),
            cancel: () => undefined,
            cancelLabel: _t("Cancel"),
        });
    }

    async deleteComment() {
        const result = await this._onDeleteComment();
        const message =
            result.message === undefined ? _t("Comment deleted") : result.message;
        const typeNotif = result.success === true ? "success" : "danger";
        this.notificationService.add(message, {
            type: typeNotif,
            sticky: typeNotif === "danger",
        });
        this.env.bus.trigger("SOCIAL:RELOAD_COMMENTS");
        if (result.success === true) {
            this.env.bus.trigger("SOCIAL:RELOAD_ORGANIZATION", {
                account_id: this.props.post.account_id.raw_value,
                post_id: this.props.post.remote_ref.raw_value,
            });
        }
    }

    /**
     * Whether the media behind this comment implements the recommendation.
     *
     * `action_like_comment` is an empty hook in `social.post.account` and its
     * stub answers success, so a connector that does not override it would
     * raise the rainbow-man for a like that never left Odoo. A connector that
     * recommends says so by overriding this, and only then is the entry
     * offered.
     *
     * @returns {Boolean} Whether the comment can be recommended from here.
     */
    canLikeComment() {
        return false;
    }

    async onLikeComment() {
        const response = await this.socialService.likeComment(
            this.props.post.id.raw_value,
            this.props.socialComment.remote_ref,
            this.props.post.account_remote_ref.raw_value
        );
        if (response.success) {
            this.effectService.add({
                type: "rainbow_man",
                message: _t("You have liked the comment."),
                imgUrl: "/social_media_base/static/src/img/like.png",
                fadeout: "fast",
            });
        } else {
            // The message comes from the social media, it is not a literal
            // the translation extractor can collect.
            this.notificationService.add(response.message, {type: "info"});
            if (response.post_deleted) {
                // The like is what revealed the publication is gone, so the
                // card behind the dialog is stale until it is refreshed.
                this.env.bus.trigger("SOCIAL:RELOAD_ORGANIZATION", {
                    account_id: this.props.post.account_id.raw_value,
                    post_id: this.props.post.remote_ref.raw_value,
                });
            }
        }
    }

    /**
     * Aim the composer of the dialog at this comment.
     *
     * There is no per-connector hook here: the reply travels the same way a
     * first-level comment does, with the target inside `post_data`, so the
     * only thing to do is to say which comment is being answered.
     */
    onReplyComment() {
        this.socialService.toggleReplyTarget(
            this.props.socialComment.remote_ref,
            this.props.socialComment.actor
        );
    }
}

// A comment draws its own replies, so the component is one of its own
// children. It is registered after the class instead of inside it, which is
// how OWL declares a recursive component.
SocialComment.components = {...SocialComment.components, SocialComment};
