import {SocialComment} from "@social_media_base/components/social_comment/social_comment.esm";
import {browser} from "@web/core/browser/browser";
import {patch} from "@web/core/utils/patch";
import {useService} from "@web/core/utils/hooks";

patch(SocialComment.prototype, {
    setup() {
        super.setup();
        this.socialFacebookService = useService("social_facebook_service");
    },

    /**
     * Replies to a Facebook comment.
     *
     * This method calls the backend API to post a reply to a Facebook comment.
     *
     * @param {String} message - The reply message
     * @returns {Object} Result with success status and message
     */
    async _onReplyComment(message) {
        // Only handle Facebook comments
        if (this.props.post.media_type.raw_value !== "facebook") {
            return super._onReplyComment(message);
        }

        try {
            const result = await this.socialFacebookService.replyToFacebookComment(
                this.props.socialComment.id,
                message
            );

            if (result && result.success) {
                return {
                    success: true,
                    message: result.message || "Reply sent successfully",
                };
            }
            return {
                success: false,
                message: result.message || "Failed to send reply",
            };
        } catch (error) {
            browser.console.error("Error replying to Facebook comment:", error);
            return {
                success: false,
                message: "An error occurred while sending the reply",
            };
        }
    },

    /**
     * Hides a Facebook comment.
     *
     * This method calls the backend API to hide a Facebook comment.
     *
     * @returns {Object} Result with success status and message
     */
    async _onDeleteComment() {
        // Only handle Facebook comments
        if (this.props.post.media_type.raw_value !== "facebook") {
            return super._onDeleteComment();
        }

        try {
            const result = await this.socialFacebookService.deleteFacebookComment(
                this.props.socialComment.id
            );

            if (result && result.success) {
                return {
                    success: true,
                    message: result.message || "Comment hidden successfully",
                };
            }
            return {
                success: false,
                message: result.message || "Failed to hide comment",
            };
        } catch (error) {
            browser.console.error("Error hiding Facebook comment:", error);
            return {
                success: false,
                message: "An error occurred while hiding the comment",
            };
        }
    },

    /**
     * Returns the list of media types for which liking a comment is not
     * supported.
     *
     * Facebook does not support liking comments via API.
     *
     * @returns {String[]} Array containing 'facebook'
     */
    mediaNotLikeEnable() {
        return ["facebook"];
    },
});
