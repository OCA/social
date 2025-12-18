import {registry} from "@web/core/registry";

export const socialFacebookService = {
    dependencies: ["orm"],

    async start(env, {orm}) {
        return {
            /**
             * Hide a comment on a Facebook post.
             * @param {Number} comment_id - The id of the social.comment record
             * @returns {Promise<Object>} The result of the server call to hide a comment
             */
            async deleteFacebookComment(comment_id) {
                if (!comment_id) {
                    return {};
                }
                return await orm.call("social.comment", "action_hide", [comment_id]);
            },

            /**
             * Reply to a Facebook comment.
             * @param {Number} comment_id - The id of the social.comment record
             * @param {String} message - The reply message
             * @returns {Promise<Object>} The result of the server call
             */
            async replyToFacebookComment(comment_id, message) {
                if (!comment_id || !message) {
                    return {};
                }
                return await orm.call("social.comment", "action_reply", [comment_id], {
                    message: message,
                });
            },

            /**
             * Sync Facebook content for an account.
             * @param {Number} account_id - The id of the social.account record
             * @returns {Promise<Object>} The result of the sync operation
             */
            async syncFacebookContent(account_id) {
                if (!account_id) {
                    return {};
                }
                return await orm.call(
                    "social.account",
                    "action_sync_facebook_content",
                    [account_id]
                );
            },

            /**
             * Sync comments for a specific post from Facebook.
             * @param {Number} account_id - The id of the social.account record
             * @param {Number} post_account_id - The id of the social.post.account record
             * @returns {Promise<Object>} The result with comments synced count
             */
            async syncCommentsForPost(account_id, post_account_id) {
                if (!account_id || !post_account_id) {
                    return {
                        success: false,
                        message: "Missing account_id or post_account_id",
                        comments_synced: 0,
                    };
                }
                return await orm.call(
                    "social.account",
                    "action_sync_comments_for_post",
                    [account_id],
                    {post_account_id: post_account_id}
                );
            },

            /**
             * Refresh Facebook access token.
             * @param {Number} account_id - The id of the social.account record
             * @returns {Promise<Object>} The result of the token refresh
             */
            async refreshFacebookToken(account_id) {
                if (!account_id) {
                    return {};
                }
                return await orm.call(
                    "social.account",
                    "action_refresh_facebook_token",
                    [account_id]
                );
            },

            /**
             * Post a new parent comment to a Facebook post.
             * @param {Number} account_id - The id of the social.account record
             * @param {Number} post_account_id - The id of the social.post.account record
             * @param {String} message - The comment message
             * @returns {Promise<Object>} The result of posting the comment
             */
            async postNewComment(account_id, post_account_id, message) {
                if (!account_id || !post_account_id || !message) {
                    return {
                        success: false,
                        message: "Missing required parameters",
                    };
                }
                return await orm.call(
                    "social.post.account",
                    "action_post_comment",
                    [post_account_id],
                    {message: message}
                );
            },
        };
    },
};

registry.category("services").add("social_facebook_service", socialFacebookService);
