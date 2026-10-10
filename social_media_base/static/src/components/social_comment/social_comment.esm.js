import {Component, useRef, useState} from "@odoo/owl";

import {browser} from "@web/core/browser/browser";
import {ConfirmationDialog} from "@web/core/confirmation_dialog/confirmation_dialog";
import {Dropdown} from "@web/core/dropdown/dropdown";
import {DropdownItem} from "@web/core/dropdown/dropdown_item";
import {useEmojiPicker} from "@web/core/emoji_picker/emoji_picker";
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

        // Initialize state for reply input and nested replies toggle
        this.state = useState({
            showReplyInput: false,
            replyMessage: "",
            // Collapse replies by default
            showReplies: false,
        });

        // Emoji picker for reply
        this.replyEmojiButtonRef = useRef("replyEmojiButton");
        this.emojiPicker = useEmojiPicker(this.replyEmojiButtonRef, {
            onSelect: (emoji) => {
                this.state.replyMessage += emoji;
            },
        });
    }

    /**
     * Toggle showing/hiding nested replies
     */
    toggleReplies() {
        this.state.showReplies = !this.state.showReplies;
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
            title: _t("Hide comment"),
            body: _t("Are you sure you want to hide this comment?"),
            confirm: () => this.deleteComment(),
            confirmLabel: _t("Hide"),
            cancel: () => {
                // Cancel
            },
            cancelLabel: _t("Cancel"),
        });
    }

    /**
     * Deletes a comment.
     *
     * This method calls `_onDeleteComment` and notifies the user of the result.
     * It also triggers a bus event to reload the comments.
     */
    async deleteComment() {
        const result = await this._onDeleteComment();
        const message =
            result.message === undefined ? _t("Comment hidden") : result.message;
        const type_notif = result.success === true ? "success" : "danger";
        this.notificationService.add(message, {
            type: type_notif,
            sticky: type_notif === "danger",
        });
        this.env.bus.trigger("SOCIAL:RELOAD_COMMENTS");
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
            this.props.post.linkedin_account_urn.raw_value
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
     * @param {String} message - The reply message
     * @returns {Object}
     */
    async _onReplyComment() {
        return {};
    }

    /**
     * Shows the reply input field.
     *
     * This method toggles the visibility of the reply input textarea.
     * Also clears any existing reply message to ensure fresh start.
     */
    onReplyComment() {
        this.state.showReplyInput = true;
        // Clear any previous message
        this.state.replyMessage = "";
    }

    /**
     * Sends a reply to the comment.
     *
     * This method validates the reply message, calls the backend API,
     * and notifies the user of the result. It also triggers a bus event
     * to reload the comments.
     */
    async sendReply() {
        if (!this.state.replyMessage || !this.state.replyMessage.trim()) {
            return;
        }

        const result = await this._onReplyComment(this.state.replyMessage);

        if (result.success) {
            this.notificationService.add(
                result.message || _t("Reply sent successfully"),
                {type: "success"}
            );
            // Clear message but keep reply input open for adding more replies
            this.state.replyMessage = "";
            // Delay reload slightly to allow user to see success message and add more replies
            browser.setTimeout(() => {
                this.env.bus.trigger("SOCIAL:RELOAD_COMMENTS");
                // Trigger reload of the kanban view to update comment count
                this.env.bus.trigger("SOCIAL:RELOAD_ORGANIZATION", {
                    reload: true,
                });
            }, 1000);
        } else {
            this.notificationService.add(result.message || _t("Failed to send reply"), {
                type: "danger",
                sticky: true,
            });
        }
    }
}
