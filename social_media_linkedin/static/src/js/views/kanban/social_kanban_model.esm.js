/** @odoo-module **/

import {SocialKanbanModel} from "@social_media_base/js/views/kanban/social_kanban_model.esm";
import {patch} from "@web/core/utils/patch";

patch(SocialKanbanModel.prototype, {
    /** @override */
    async onLikePost(record) {
        super.onLikePost(record);
        const post_id = record.id.raw_value;
        const author_urn = record.account_remote_ref.value;
        const result = await this.orm.silent.call(
            "social.post.account",
            "action_like_post",
            [[post_id], author_urn]
        );
        this.env.bus.trigger("SOCIAL:RELOAD_ORGANIZATION", {
            account_id: record.account_id.raw_value,
            post_id: record.remote_ref.raw_value,
        });
        return result;
    },
});
