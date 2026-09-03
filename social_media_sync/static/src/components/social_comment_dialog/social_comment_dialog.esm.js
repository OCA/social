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
import {SocialImageDialog} from "@social_media_base/components/social_image_dialog/social_image_dialog.esm";
import {SocialMessage} from "@social_media_base/components/social_message/social_message.esm";
import {_t} from "@web/core/l10n/translation";

export class SocialCommentDialog extends Component {
    static template = "social_media_base.SocialCommentDialog";
    static components = {
        Dialog,
        Composer,
        SocialComment,
        // The dialog shares the block of the card with the kanban views, and
        // that block draws the message with this component. The dialog shows
        // the message whole, so the branch is never taken, but the template
        // is the same one and it is resolved against the components of
        // whoever calls it.
        SocialMessage,
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
        this.record = this.props.post;
        // The aim of the composer lives in the service, and the placeholder
        // has to redraw when a comment takes it or gives it back.
        this.socialState = useState(this.socialService.state);
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
            if (result && result.success) {
                this.state.comments = result.data || [];
            } else {
                this.notificationService.add(
                    (result && result.message) || _t("Error retrieving comments"),
                    {
                        type: "danger",
                    }
                );
            }
        });

        useBus(this.env.bus, "SOCIAL:RELOAD_COMMENTS", async () => {
            await this.updateListComments();
        });

        onMounted(() => {
            this.intervalRefreshComment = setInterval(() => {
                this.updateListComments();
            }, 120000);
        });

        onWillUnmount(() => {
            clearInterval(this.intervalRefreshComment);
            // A target left behind would greet the next dialog with a banner
            // for a comment that is no longer on screen.
            this.socialService.clearReplyTarget();
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
                        const typeNotif =
                            payload.success === true ? "success" : "danger";
                        // The comment has already been published: whatever
                        // it answered to, the next one starts clean.
                        this.socialService.clearReplyTarget();
                        this.notificationService.add(message, {
                            type: typeNotif,
                        });
                        // Reading the comments of a publication the social
                        // media just reported as gone would only fail again,
                        // so the dialog closes instead of reloading them.
                        if (!payload.post_deleted) {
                            this.env.bus.trigger("SOCIAL:RELOAD_COMMENTS");
                        }
                        this.env.bus.trigger("SOCIAL:RELOAD_ORGANIZATION", {
                            account_id: this.props.account.raw_value,
                            post_id: this.props.post.remote_ref.raw_value,
                        });
                        if (payload.post_deleted) {
                            this.props.close();
                        }
                    }
                });
            }
        };
        // The dependencies are empty on purpose: without them the listener
        // is torn down and registered again on every render.
        useEffect(
            () => {
                this.busService.addEventListener("notification", handleNotification);
                return () => {
                    this.busService.removeEventListener(
                        "notification",
                        handleNotification
                    );
                };
            },
            () => []
        );
    }

    get commentsByRef() {
        return new Map(
            this.state.comments.map((comment) => [comment.remote_ref, comment])
        );
    }

    /**
     * The first-level comment a comment ends up hanging from.
     *
     * X answers the whole conversation, replies of replies included, and
     * those are drawn under the comment that started the branch instead of
     * one level deeper: LinkedIn does not nest beyond one level and offering
     * a third one on X alone is the asymmetry this avoids. A comment whose
     * parent is not in the list — the reference did not travel, or the parent
     * is the publication — is a first-level one and answers for itself.
     *
     * @param {Object} comment The comment being placed.
     * @returns {String} The reference of the comment that starts its branch.
     */
    rootRefOf(comment) {
        const byRef = this.commentsByRef;
        const seen = new Set();
        let current = comment;
        while (current.parent_ref && byRef.has(current.parent_ref)) {
            if (seen.has(current.remote_ref)) {
                break;
            }
            seen.add(current.remote_ref);
            current = byRef.get(current.parent_ref);
        }
        return current.remote_ref;
    }

    /** The comments hanging from the publication. */
    get comments() {
        return this.state.comments.filter(
            (comment) => this.rootRefOf(comment) === comment.remote_ref
        );
    }

    repliesOf(comment) {
        return this.state.comments.filter(
            (reply) =>
                reply.remote_ref !== comment.remote_ref &&
                this.rootRefOf(reply) === comment.remote_ref
        );
    }

    onShowAllImages(ev) {
        ev.stopPropagation();
        this.dialogService.add(SocialImageDialog, {
            title: _t("All Images"),
            images: JSON.parse(this.props.post.image_urls.raw_value),
        });
    }

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
     * The comment is published on the social media, not logged as a note.
     *
     * There is one composer for the whole dialog, so when a comment is being
     * answered the placeholder is what says so: the social media does not
     * always give the name of who wrote it — LinkedIn answers a URN — and a
     * banner naming nobody says less than this.
     */
    get composerPlaceholder() {
        if (this.socialState.replyTarget) {
            return _t("Write your reply…");
        }
        const account = this.record.author?.value || this.props.account.value;
        return _t("Comment as %(account)s…", {account});
    }

    get renderingContext() {
        return {
            luxon,
            record: this.record,
            images: this.props.images,
            isDialog: true,
            onShowAllImages: this.onShowAllImages.bind(this),
        };
    }
}
