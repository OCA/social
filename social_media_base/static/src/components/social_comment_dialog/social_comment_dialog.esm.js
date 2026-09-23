import {
    Component,
    onMounted,
    onWillStart,
    onWillUnmount,
    useEffect,
    useRef,
    useState,
} from "@odoo/owl";
import {useBus, useService} from "@web/core/utils/hooks";
import {browser} from "@web/core/browser/browser";
import {Dialog} from "@web/core/dialog/dialog";
import {SocialComment} from "../social_comment/social_comment.esm";
import {SocialImageDialog} from "../social_image_dialog/social_image_dialog.esm";
import {_t} from "@web/core/l10n/translation";
import {useEmojiPicker} from "@web/core/emoji_picker/emoji_picker";

export class SocialCommentDialog extends Component {
    static template = "social_media_base.SocialCommentDialog";
    static components = {
        Dialog,
        SocialComment,
    };
    static props = {
        title: {type: String, required: true},
        images: {type: Array, required: true},
        post: {type: Object, required: true},
        account: {type: Object, required: true},
        media_type: {type: Object, required: true},
        close: {type: Function},
    };

    setup() {
        super.setup();
        this.dialogService = useService("dialog");
        this.socialService = useService("social_service");
        // Note: mail.thread service removed - not available in Odoo 18
        this.notificationService = useService("notification");
        this.busService = this.env.services.bus_service;
        this.state = useState({
            comments: [],
            account_id: this.props.account.raw_value,
            // New comment composer state
            newComment: "",
            // Files to upload with comment
            attachments: [],
        });

        // Emoji picker for new comment
        this.emojiButtonRef = useRef("emojiButton");
        this.emojiPicker = useEmojiPicker(this.emojiButtonRef, {
            onSelect: (emoji) => {
                this.state.newComment += emoji;
            },
        });

        // File input refs
        this.fileInputRef = useRef("fileInput");
        this.cameraInputRef = useRef("cameraInput");
        onWillStart(async () => {
            const result = await this.socialService.getComments(
                this.props.post.id.raw_value
            );
            if (result && "success" in result && "data" in result && result.success) {
                this.state.comments = result.data;
            } else {
                this.notificationService.add(
                    result.message || _t("Error retrieving comments"),
                    {
                        type: "danger",
                    }
                );
            }
        });

        useBus(this.env.bus, "SOCIAL:RELOAD_COMMENTS", async () => {
            await this.updateListComments();
        });

        // Refresh comments every 30 seconds
        onMounted(() => {
            this.intervalRefreshComment = browser.setInterval(() => {
                this.updateListComments();
            }, 120000);
        });

        onWillUnmount(() => {
            browser.clearInterval(this.intervalRefreshComment);
        });

        const handleNotification = ({detail: notifications}) => {
            if (notifications && notifications.length > 0) {
                notifications.forEach((notif) => {
                    const {payload, type} = notif;
                    if (type === "comments" && payload) {
                        const message =
                            payload === undefined || payload.message === undefined
                                ? _t("Comment created")
                                : payload.message;
                        const type_notif =
                            payload.success === true ? "success" : "danger";
                        this.env.bus.trigger("SOCIAL:RELOAD_COMMENTS");
                        this.notificationService.add(message, {
                            type: type_notif,
                        });
                        this.env.bus.trigger("SOCIAL:RELOAD_ORGANIZATION", {
                            account_id: this.props.account.raw_value,
                            post_id:
                                this.props.post.linkedin_post_account_urn.raw_value,
                        });
                    }
                });
            }
        };
        useEffect(() => {
            this.busService.addEventListener("notification", handleNotification);
            return () => {
                this.busService.removeEventListener("notification", handleNotification);
            };
        });
    }

    /**
     * A getter for the comments state.
     *
     * @returns {Array<Object>}
     *   An array of comments. Each comment object has the following properties:
     *   - `id`: The comment's ID.
     *   - `author_id`: The ID of the user who wrote the comment.
     *   - `author_name`: The name of the user who wrote the comment.
     *   - `content`: The content of the comment.
     *   - `create_date`: The timestamp when the comment was created.
     */
    get comments() {
        return this.state.comments;
    }

    /**
     * Opens a dialog to show all images in the post.
     *
     * This method is called when the "Show all images" button is clicked.
     * It stops the event propagation and opens a dialog with all images
     * in the post.
     *
     * @param {Event} ev - The click event on the "Show all images" button.
     */
    onShowAllImages(ev) {
        ev.stopPropagation();
        this.dialogService.add(SocialImageDialog, {
            title: _t("All Images"),
            images: JSON.parse(this.props.post.image_urls.raw_value),
        });
    }

    /**
     * Updates the list of comments for the post.
     *
     * - Calls the `getComments` method of the `socialService` to retrieve the
     *   list of comments for the post.
     * - Sets the `comments` state with the retrieved list of comments.
     *
     * @returns {Promise<void>}
     *   The promise resolved when the comments are retrieved and the state is
     *   updated.
     */
    async updateListComments() {
        const result = await this.socialService.getComments(
            this.props.post.id.raw_value
        );
        this.state.comments = result?.data ?? [];
    }

    _commentAllowUpload() {
        return true;
    }

    get commentAllowUpload() {
        return this._commentAllowUpload();
    }

    /**
     * Send a new comment (parent comment, not a reply)
     *
     * This method is overridden by platform-specific implementations
     * to post the comment to the social platform.
     */
    async _sendNewComment() {
        // Base implementation - to be overridden by subclasses
        return {
            success: false,
            message: "Not implemented for this platform",
        };
    }

    /**
     * Handle file selection
     */
    onFileChange(ev) {
        const files = Array.from(ev.target.files);
        this.state.attachments = [...this.state.attachments, ...files];
        // Reset input so same file can be selected again
        ev.target.value = "";
    }

    /**
     * Remove attachment from list
     */
    removeAttachment(index) {
        this.state.attachments.splice(index, 1);
    }

    /**
     * Send new comment button handler
     *
     * Posts a new parent comment to the social platform
     */
    async sendNewComment() {
        if (!this.state.newComment || !this.state.newComment.trim()) {
            return;
        }

        const result = await this._sendNewComment(
            this.state.newComment,
            this.state.attachments
        );

        if (result.success) {
            this.notificationService.add(
                result.message || _t("Comment posted successfully"),
                {type: "success"}
            );
            this.state.newComment = "";
            this.state.attachments = [];
            await this.updateListComments();
            // Trigger reload of the kanban view to update comment count
            this.env.bus.trigger("SOCIAL:RELOAD_ORGANIZATION", {
                reload: true,
            });
        } else {
            this.notificationService.add(
                result.message || _t("Failed to post comment"),
                {type: "danger", sticky: true}
            );
        }
    }
}
