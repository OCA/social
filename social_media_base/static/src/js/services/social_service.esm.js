/** @odoo-module */

import {registry} from "@web/core/registry";

export const socialService = {
    dependencies: ["orm"],

    /**
     * Service to interact with social network posts and comments.
     *
     * Returns an object with the following methods:
     * - `getComments`: Retrieves comments for a given post account.
     * - `likeComment`: Likes a comment on a social network post.
     *
     * @param {Object} env - web environment
     * @param {Object} services - services to use
     * @param {Object} services.orm - ORM service
     * @returns {Object} - an object with the methods `getComments` and `likeComment`
     */
    async start(env, {orm}) {
        return {
            /**
             * Retrieve comments for a given post account
             * @param {Number} post_account_id - id of the post account
             * @returns {Promise<Array<Object>>} - an array of comments
             */
            async getComments(post_account_id = null) {
                if (!post_account_id) {
                    return [];
                }
                return await orm.call("social.post.account", "get_comments", [
                    post_account_id,
                ]);
            },
            /**
             * Likes a comment on a social network post.
             *
             * This method calls the backend to like a comment associated with a given post account.
             *
             * @param {Number} post_account_id - The ID of the post account to which the comment belongs.
             * @param {Number} comment_id - The ID of the comment to like.
             * @param {String} actor_urn - The URN of the actor performing the like action.
             * @returns {Promise<Object>} - A promise that resolves to an object containing the success status and a message.
             */
            async likeComment(post_account_id, comment_id, actor_urn) {
                if (!post_account_id || !comment_id || !actor_urn) {
                    return {
                        success: false,
                        message: "An error occurred while liking the comment",
                    };
                }
                return await orm.call("social.post.account", "action_like_comment", [
                    [post_account_id],
                    comment_id,
                    actor_urn,
                ]);
            },
        };
    },
};

registry.category("services").add("social_service", socialService);
