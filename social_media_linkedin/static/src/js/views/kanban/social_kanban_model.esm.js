/** @odoo-module **/

import {SocialKanbanModel} from "@social_media_base/js/views/kanban/social_kanban_model.esm";
import {patch} from "@web/core/utils/patch";

patch(SocialKanbanModel.prototype, {
    /**
     * Handles the like button click for a post in the kanban view
     * @param {Object} record - the current record
     * @returns {Promise} resolves with the result of the RPC call
     */
    async onLikePost(record) {
        super.onLikePost();
        const post_id = record.id.raw_value;
        const author_urn = record.linkedin_account_urn.value;
        const result = await this.orm.silent.call(
            "social.post.account",
            "action_like_post",
            [[post_id], author_urn]
        );
        this.env.bus.trigger("SOCIAL:RELOAD_ORGANIZATION", {
            account_id: record.account_id.raw_value,
            post_id: record.linkedin_post_account_urn.raw_value,
        });
        return result;
    },

    _get_select_fields(media) {
        var res = super._get_select_fields(media);
        if (media === "linkedin") {
            res.push("linkedin_account_urn", "image_1920");
        }
        return res;
    },
});
