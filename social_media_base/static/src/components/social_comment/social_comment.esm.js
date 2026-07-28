/** @odoo-module **/

import {Component} from "@odoo/owl";
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
    };

    /**
     * Sets up the component's services.
     *
     * This method is called once, when the component is set up.
     * It sets up the component's services and initializes its state.
     */
    setup() {
        super.setup();
        this.socialService = useService("social_service");
        this.notificationService = useService("notification");
        this.effectService = useService("effect");
        this.dialog = useService("dialog");
    }

    /**
     * Delete a comment.
     *
     * This method is overridden by subclasses to implement the logic to delete a
     * comment. It should return an object with a `success` property set to `true`
     * if the comment was deleted successfully, and a `message` property set to
     * the message to display to the user.
     *
     * @returns {Object}
     */
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

    /**
     * Deletes a comment.
     *
     * This method calls `_onDeleteComment` and notifies the user of the result.
     * It also triggers the bus events to reload the comments and, when the
     * deletion succeeded, the post statistics, so the comment counter of the
     * card stays in sync.
     */
    async deleteComment() {
        const result = await this._onDeleteComment();
        const message =
            result.message === undefined ? _t("Comment deleted") : result.message;
        const type_notif = result.success === true ? "success" : "danger";
        this.notificationService.add(message, {
            type: type_notif,
            sticky: type_notif === "danger",
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
     * Returns the list of media types for which liking a comment is not
     * supported.
     *
     * This method is overridden by subclasses to implement the logic to
     * determine the list of media types for which liking a comment is not
     * supported. It should return an array of strings, where each string is
     * a media type.
     *
     * @returns {String[]}
     */
    mediaNotLikeEnable() {
        return [];
    }

    /**
     * Likes a comment.
     *
     * This method calls `likeComment` on the social service and notifies the
     * user of the result. It also triggers a bus event to reload the comments.
     */
    async onLikeComment() {
        const response = await this.socialService.likeComment(
            this.props.post.id.raw_value,
            this.props.socialComment.id,
            this.props.post.account_remote_ref.raw_value
        );
        if (response.success) {
            this.effectService.add({
                type: "rainbow_man",
                message: _t("You have liked the post."),
                imgUrl: "/social_media_base/static/src/img/like.png",
                fadeout: "fast",
            });
        } else {
            this.notificationService.add(_t(response.message), {type: "info"});
        }
    }

    /**
     * Replies to a comment.
     *
     * This method is overridden by subclasses to implement the logic to reply
     * to a comment. It should return an object with a `success` property set to
     * `true` if the comment was replied successfully, and a `message` property
     * set to the message to display to the user.
     *
     * @returns {Object}
     */
    _onReplyComment() {
        return {};
    }

    /**
     * Replies to a comment.
     *
     * This method triggers a bus event to reload the comments.
     */
    onReplyComment() {
        this.env.bus.trigger("SOCIAL:RELOAD_COMMENTS");
    }
}
