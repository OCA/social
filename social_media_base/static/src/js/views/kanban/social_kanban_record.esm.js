/** @odoo-module **/
import {onWillStart, useEffect, useRef} from "@odoo/owl";
import {KanbanRecord} from "@web/views/kanban/kanban_record";
import {SocialCommentDialog} from "@social_media_base/components/social_comment_dialog/social_comment_dialog.esm";
import {SocialPostAccountMixin} from "@social_media_base/js/app/social_media_base_mixins.esm";
import {_t} from "@web/core/l10n/translation";
import {useService} from "@web/core/utils/hooks";

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
            if (this.record.published_date) {
                // Store both formatted date and relative time
                const publishedDateTime = luxon.DateTime.fromISO(
                    this.record.published_date.raw_value
                );
                this.record.published_date_formatted = publishedDateTime.toFormat("d/M/y");
                this.record.published_date_relative = this._getRelativeTime(publishedDateTime);
                this.record.published_date = this.record.published_date_relative;
            }
            // Format numbers with thousand separators
            this._formatMetrics();
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
     * - If post has external URL, opens it in new tab
     * - If no external URL, opens the post form view in Odoo
     * - Calls the parent class's `onGlobalClick` method.
     *
     * @param {MouseEvent} ev - The global click event.
     */
    async onGlobalClick(ev) {
        const kanban_social = ev.target.closest("div.oe_kanban_social_dashboard");

        if (kanban_social !== null) {
            // If post has an external URL (Facebook/social media link), open it
            if (this.record.post_account_url && this.record.post_account_url.raw_value) {
                const post_exist = await this.validPostExist();
                if (post_exist) {
                    window.open(this.record.post_account_url.value, "_blank");
                } else {
                    this.messagePostNotExist();
                    this.env.model.load();
                }
            } else {
                // If no external URL, open the Odoo form view for this post
                // This happens for draft posts or synced posts without URLs
                ev.stopPropagation();
                this.env.model.action.doAction({
                    type: "ir.actions.act_window",
                    res_model: this.props.record.resModel,
                    res_id: this.props.record.resId,
                    views: [[false, "form"]],
                    target: "current",
                });
                return;
            }
        }
        return super.onGlobalClick(ev);
    }

    /**
     * Get relative time string (e.g., "1 hour", "2 hours", "3 days")
     *
     * @param {luxon.DateTime} dateTime - The datetime to convert
     * @returns {string} Relative time string
     */
    _getRelativeTime(dateTime) {
        const now = luxon.DateTime.now();
        const diff = now.diff(dateTime, ['years', 'months', 'days', 'hours', 'minutes']).toObject();

        if (diff.years >= 1) {
            const years = Math.floor(diff.years);
            return years === 1 ? "1 year" : `${years} years`;
        } else if (diff.months >= 1) {
            const months = Math.floor(diff.months);
            return months === 1 ? "1 month" : `${months} months`;
        } else if (diff.days >= 1) {
            const days = Math.floor(diff.days);
            return days === 1 ? "1 day" : `${days} days`;
        } else if (diff.hours >= 1) {
            const hours = Math.floor(diff.hours);
            return hours === 1 ? "1 hour" : `${hours} hours`;
        } else if (diff.minutes >= 1) {
            const minutes = Math.floor(diff.minutes);
            return minutes === 1 ? "1 minute" : `${minutes} minutes`;
        } else {
            return "Just now";
        }
    }

    /**
     * Format numbers with thousand separators
     * Formats: 9911 -> 9,911 | 87618 -> 87,618
     */
    _formatMetrics() {
        const formatNumber = (num) => {
            if (!num && num !== 0) return '0';
            return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
        };

        // Format like_count
        if (this.record.like_count) {
            this.record.like_count_formatted = formatNumber(this.record.like_count.value);
        }

        // Format comment_count
        if (this.record.comment_count) {
            this.record.comment_count_formatted = formatNumber(this.record.comment_count.value);
        }

        // Format share_count (if exists)
        if (this.record.share_count) {
            this.record.share_count_formatted = formatNumber(this.record.share_count.value);
        }

        // Format views (if exists)
        if (this.record.view_count) {
            this.record.view_count_formatted = formatNumber(this.record.view_count.value);
        }
    }
}

SocialKanbanRecord.components = {
    ...KanbanRecord.components,
};
