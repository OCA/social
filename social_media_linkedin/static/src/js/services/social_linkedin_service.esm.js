/** @odoo-module */

import {registry} from "@web/core/registry";

export const socialLinkedinService = {
    dependencies: ["orm"],

    async start(env, {orm}) {
        return {
            async deleteLinkedinComment(postAccountId, commentId, actorUrn) {
                if (!postAccountId) {
                    return [];
                }
                return await orm.call(
                    "social.post.account",
                    "delete_linkedin_comment",
                    [postAccountId, commentId, actorUrn]
                );
            },
        };
    },
};

registry.category("services").add("social_linkedin_service", socialLinkedinService);
