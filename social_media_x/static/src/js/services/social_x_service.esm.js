/** @odoo-module */

import {registry} from "@web/core/registry";

export const socialXService = {
    dependencies: ["orm"],

    /**
     * Returns an object with the following methods:
     * - `createXComment`: Creates a comment on a social network post.
     *
     * @param {Object} env - web environment
     * @param {Object} services - services to use
     * @param {Object} services.orm - ORM service
     * @returns {Object} - an object with the methods `createXComment`
     */
    async start(env, {orm}) {
        return {
            async validPostXExist(post_account_id) {
                if (!post_account_id) {
                    return false;
                }
                return await orm.call("social.post.account", "get_post_x", [
                    post_account_id,
                ]);
            },
        };
    },
};

registry.category("services").add("social_x_service", socialXService);
