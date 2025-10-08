/** @odoo-module **/

import {
    Component,
    onMounted,
    onWillStart,
    onWillUnmount,
    useEffect,
    useState,
} from "@odoo/owl";
import {useBus, useService} from "@web/core/utils/hooks";
import {Composer} from "@mail/core/common/composer";
import {Dialog} from "@web/core/dialog/dialog";
import {SocialComment} from "../social_comment/social_comment.esm";
import {SocialImageDialog} from "../social_image_dialog/social_image_dialog.esm";
import {_t} from "@web/core/l10n/translation";

export class SocialCommentDialog extends Component {
    static template = "social_media_base.SocialCommentDialog";
    static components = {
        Dialog,
        Composer,
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
        this.threadService = useService("mail.thread");
        this.notificationService = useService("notification");
        this.busService = this.env.services.bus_service;
        this.state = useState({
            thread: undefined,
            comments: [],
            account_id: this.props.account.raw_value,
        });
        onWillStart(async () => {
            this.state.thread = this.threadService.getThread(
                "social.post.account",
                this.props.post.id.value
            );
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
            this.intervalRefreshComment = setInterval(() => {
                this.updateListComments();
            }, 120000);
        });

        onWillUnmount(() => {
            clearInterval(this.intervalRefreshComment);
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
}
