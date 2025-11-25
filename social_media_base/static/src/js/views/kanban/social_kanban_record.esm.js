import {onWillStart, useEffect, useRef} from "@odoo/owl";
import {KanbanRecord} from "@web/views/kanban/kanban_record";
import {SocialCommentDialog} from "@social_media_base/components/social_comment_dialog/social_comment_dialog.esm";
import {SocialPostAccountMixin} from "@social_media_base/js/app/social_media_base_mixins.esm";
import {_t} from "@web/core/l10n/translation";
import {useService} from "@web/core/utils/hooks";
const {window} = globalThis;

export class SocialKanbanRecord extends SocialPostAccountMixin(KanbanRecord) {
    /**
     * Called when the component is initialized.
     *
     * Sets up the component with the required services, effects and event listeners.
     *
     * @override
     */
    setup() {
        super.setup();
        this.record.messageLength = 150;
        this.record.countShowImage = 2;
        this.rootRef = useRef("root");
        this.dialogService = useService("dialog");
        this.effectService = useService("effect");
        this.messageNotExistPost = _t("The post does not exist or has been deleted.");
        this.record.notAvailableLike = [];
        onWillStart(async () => {
            if (this.record.media_type) {
                this.record.accountsBasic = await this.env.model._loadAccountsBasic(
                    this.record.media_type.raw_value
                );
            }
        });

        // Show all message
        useEffect(
            (value) => {
                if (value) {
                    value.addEventListener("click", this.onShowMoreMessage.bind(this));
                    return () => {
                        value.removeEventListener(
                            "click",
                            this.onShowMoreMessage.bind(this)
                        );
                    };
                }
            },
            () => [this.rootRef.el.querySelector(".show-more-message")]
        );

        // Like or dislike post
        useEffect(
            (value) => {
                if (value) {
                    value.addEventListener("click", this.onLikePost.bind(this));
                    return () => {
                        value.removeEventListener("click", this.onLikePost.bind(this));
                    };
                }
            },
            () => [this.rootRef.el.querySelector(".social-like-post")]
        );

        // Show all images
        useEffect(
            (value) => {
                if (value) {
                    value.addEventListener("click", this.onShowAllImages.bind(this));
                    return () => {
                        value.removeEventListener(
                            "click",
                            this.onShowAllImages.bind(this)
                        );
                    };
                }
            },
            () => [this.rootRef.el.querySelector(".social-all-images")]
        );

        // Post Comments
        useEffect(
            (value) => {
                if (value) {
                    value.addEventListener("click", this.onPostComment.bind(this));
                    return () => {
                        value.removeEventListener(
                            "click",
                            this.onPostComment.bind(this)
                        );
                    };
                }
            },
            () => [this.rootRef.el.querySelector(".social-post-comment")]
        );
    }

    /**
     * Handles the click event on the "Post Comment" button.
     *
     * - Stops the event propagation.
     * - Opens a dialog with the comment form and the post images.
     *
     * @param {Event} ev - The click event on the "Post Comment" button.
     */
    onPostComment(ev) {
        ev.stopPropagation();
        this.dialogService.add(SocialCommentDialog, {
            title: _t("Post Comment"),
            account: this.record.account_id,
            post: this.record,
            media_type: this.record.media_type,
            images: JSON.parse(this.record.image_urls.raw_value),
        });
    }

    /**
     * Checks if the post exists.
     *
     * This function returns a boolean indicating whether the post exists.
     * Currently, it always returns `true`. In a real implementation, this
     * would typically involve checking the existence of the post with
     * the backend service or database.
     *
     * @returns {Boolean} `true` if the post exists, otherwise `false`.
     */
    validPostExist() {
        return true;
    }

    /**
     * Displays a notification when the post does not exist.
     *
     * - Adds a notification with the message "The post does not exist."
     *   and type "info".
     */
    messagePostNotExist() {
        this.notification.add(this.messageNotExistPost, {
            type: "info",
        });
    }

    /**
     * Handles global click events on the kanban record.
     *
     * - Checks if the clicked element is within the social dashboard.
     * - Verifies the existence of a post URL and checks if the post exists.
     * - Opens the post URL in a new tab if the post exists; otherwise, displays a notification.
     * - Calls the parent class's `onGlobalClick` method.
     *
     * @param {MouseEvent} ev - The global click event.
     */
    async onGlobalClick(ev) {
        const kanban_social = ev.target.closest("div.oe_kanban_social_dashboard");
        // Checking if the post exists
        if (kanban_social !== null && !this.record.post_account_url.value) {
            this.messagePostNotExist();
            this.env.model.load();
        } else if (kanban_social !== null && this.record.post_account_url.raw_value) {
            const post_exist = await this.validPostExist();
            if (post_exist) {
                window.open(this.record.post_account_url.value, "_blank");
            } else {
                this.messagePostNotExist();
                this.env.model.load();
            }
        }
        return super.onGlobalClick(ev);
    }
}

SocialKanbanRecord.components = {
    ...KanbanRecord.components,
};
