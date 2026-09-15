/** @odoo-module **/

import {Component, useState} from "@odoo/owl";
import {useBus, useService} from "@web/core/utils/hooks";
import {ConfirmationDialog} from "@web/core/confirmation_dialog/confirmation_dialog";
import {Dropdown} from "@web/core/dropdown/dropdown";
import {DropdownItem} from "@web/core/dropdown/dropdown_item";
import {SocialComposer} from "../social_composer/social_composer.esm";
import {_t} from "@web/core/l10n/translation";

// Drawn for a comment whose author has no picture to show. The grey
// silhouette of `base` is the one Odoo itself uses where it knows a
// person is missing, and it says exactly that: nobody in particular.
const AUTHOR_AVATAR_PLACEHOLDER = "/base/static/img/avatar_grey.png";

export class SocialComment extends Component {
    static template = "social_media_sync.SocialComment";
    static components = {
        Dropdown,
        DropdownItem,
        SocialComposer,
    };
    static props = {
        socialComment: {type: Object, required: true},
        post: {type: Object, required: true},
        // The replies already known, the ones the social media served
        // together with the comments instead of apart.
        replies: {type: Array, optional: true},
        isReply: {type: Boolean, optional: true},
        // The composer of the dialog, drawn under this comment while it is
        // the one being answered. A reply never hosts it, so it is optional.
        composer: {type: Object, optional: true},
        allowUpload: {type: Boolean, optional: true},
        // Whether a publication of the dialog is in flight. While it is, the
        // entries that would move the composer away from it are not offered.
        posting: {type: Boolean, optional: true},
        onPostingChange: {type: Function, optional: true},
        // Handed to the composer this comment hosts, so that a reply that
        // was really sent gives the composer back to the dialog.
        onPostCallback: {type: Function, optional: true},
    };
    static defaultProps = {
        replies: [],
        isReply: false,
        allowUpload: true,
        posting: false,
    };

    setup() {
        super.setup();
        this.socialService = useService("social_service");
        this.notificationService = useService("notification");
        this.effectService = useService("effect");
        this.dialog = useService("dialog");
        // The aim of the composer is shared state: the button and the
        // composer drawn under the comment redraw when another comment
        // steals it.
        this.socialState = useState(this.socialService.state);
        this.state = useState({
            expanded: false,
            loading: false,
            replies: [],
            // What the social media said without being asked. LinkedIn says
            // nothing until the replies are read, and answers `null` here.
            count: this.props.socialComment.reply_count ?? null,
            // Whether the account already reacted to this comment, as the
            // thread was read. The entry redraws from here so the answer of
            // the social media is seen without reading the thread again.
            liked: Boolean(this.props.socialComment.liked),
        });
        // A reply does not travel in the list of comments of the post, so the
        // refresh of the dialog never brings it: an unfolded branch reads
        // itself again, which is the only way a reply just published shows up
        // under the comment it answers.
        useBus(this.env.bus, "SOCIAL:RELOAD_COMMENTS", async () => {
            if (this.state.expanded && !this.props.isReply) {
                await this._loadReplies();
            }
        });
        // A reply the dialog has just drawn under this comment: the branch
        // unfolds by itself, because a reply that was published and cannot
        // be seen without unfolding reads as a reply that was lost. Nothing
        // is read from the social media here — the reply is already on the
        // list the dialog holds.
        useBus(this.env.bus, "SOCIAL:REPLY_PUBLISHED", ({detail}) => {
            if (
                !this.props.isReply &&
                detail?.parentRef === this.props.socialComment.remote_ref
            ) {
                this.state.expanded = true;
            }
        });
    }

    /**
     * The name to show for whoever wrote the comment.
     *
     * The server answers `actor` already resolved into a name to draw, and
     * the client does not guess: a connector whose API only names the actor
     * by reference resolves it before answering, and where it cannot it
     * answers a neutral label of its own.
     *
     * What is left here is the answer that carries no name at all — an
     * identifier, or the dict a comment with no stamp arrives with. That one
     * is drawn as an unknown author and never as whoever published: signing
     * a comment with the name of the account is telling the user something
     * false about who said what.
     *
     * @returns {String} The name to draw in the header.
     */
    get authorName() {
        const actor = this.props.socialComment.actor;
        if (typeof actor === "string" && actor && !actor.startsWith("urn:")) {
            return actor;
        }
        return _t("Unknown author");
    }

    /**
     * The picture of whoever wrote the comment.
     *
     * Never the avatar of the account, for the same reason `authorName` is
     * never its name: the logo of the page next to a comment somebody else
     * wrote attributes it to the page.
     *
     * @returns {String} The picture of the author, or a generic silhouette.
     */
    get authorAvatarUrl() {
        return this.props.socialComment.author_image || AUTHOR_AVATAR_PLACEHOLDER;
    }

    get isReplyTarget() {
        return (
            this.socialState.replyTarget?.commentRef ===
            this.props.socialComment.remote_ref
        );
    }

    /**
     * Whether the composer of the dialog is drawn under this comment.
     *
     * Only the dialog hands the composer down, and only to the comments it
     * draws at first level: a reply never receives one, so being the aim of
     * the composer is all this comment has to answer for.
     */
    get hostsComposer() {
        return Boolean(this.props.composer) && this.isReplyTarget;
    }

    get replyPlaceholder() {
        return _t("Write your reply…");
    }

    /**
     * The replies of this comment, from wherever they arrived.
     *
     * Two sources feed the same branch and neither one replaces the other:
     * what travelled with the comments of the post —the whole conversation
     * on X, a reply just published on any social media— and what unfolding
     * the branch read. Preferring one would hide the other, so they are put
     * together and what is in both is counted once.
     */
    get replies() {
        const merged = [...this.props.replies];
        const known = new Set(merged.map((reply) => reply.remote_ref));
        for (const reply of this.state.replies) {
            if (!known.has(reply.remote_ref)) {
                merged.push(reply);
                known.add(reply.remote_ref);
            }
        }
        return merged;
    }

    /**
     * How many replies the comment has.
     *
     * What the social media counted is a moment in the past —it was answered
     * when the branch was read— so a reply published since is not in it. The
     * larger of the two is the one that does not hide a reply already on
     * screen.
     */
    get repliesCount() {
        const replies = this.replies;
        return this.state.count === null || this.state.count === undefined
            ? replies.length
            : Math.max(this.state.count, replies.length);
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
        if (await this._loadReplies()) {
            this.state.expanded = true;
        }
    }

    /**
     * Read the replies of this comment from the social media.
     *
     * The list on screen is left untouched when the read fails: a branch
     * already unfolded keeps what the user was reading, exactly as the
     * dialog does with the comments of the post.
     *
     * @returns {Promise<Boolean>} Whether the replies could be read.
     */
    async _loadReplies() {
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
            return false;
        }
        this.state.replies = result.data || [];
        this.state.count = result.count ?? this.state.replies.length;
        return true;
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

    /**
     * Toggle the reaction of the account on this comment.
     *
     * A social media holds one reaction per account, so pressing the entry on
     * a comment already recommended is what withdraws it.
     */
    async onLikeComment() {
        const liked = this.state.liked;
        const react = liked
            ? this.socialService.unlikeComment.bind(this.socialService)
            : this.socialService.likeComment.bind(this.socialService);
        const response = await react(
            this.props.post.id.raw_value,
            this.props.socialComment.remote_ref,
            this.props.post.account_remote_ref.raw_value
        );
        // What the social media holds, which is not always what was asked
        // for: recommending twice answers that the reaction was already
        // there, and withdrawing one that is gone answers the same the other
        // way round. A social media that could not be read says nothing, and
        // then the entry stays as it was drawn.
        this.state.liked = response.liked ?? liked;
        if (response.success && liked) {
            this.notificationService.add(
                _t("You have withdrawn your recommendation."),
                {
                    type: "success",
                }
            );
        } else if (response.success) {
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
