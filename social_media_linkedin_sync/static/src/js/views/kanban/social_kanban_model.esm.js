/** @odoo-module **/

import {SocialKanbanModel} from "@social_media_base/js/views/kanban/social_kanban_model.esm";
import {patch} from "@web/core/utils/patch";

patch(SocialKanbanModel.prototype, {
    /** @override */
    async onLikePost(record) {
        return await this._reactLinkedinPost(record, "action_like_post");
    },

    /** @override */
    async onUnlikePost(record) {
        return await this._reactLinkedinPost(record, "action_unlike_post");
    },

    /**
     * Send the reaction of the account and refresh what the card shows.
     *
     * Creating a reaction and withdrawing one differ in nothing but the
     * method they call: both are sent under the actor of the account and
     * both leave the publication with figures Odoo has to read again.
     *
     * @param {Object} record the publication the entry was pressed on.
     * @param {String} method the method of `social.post.account` to call.
     * @returns {Promise<Object>} what the connector answered.
     */
    async _reactLinkedinPost(record, method) {
        const post_id = record.id.raw_value;
        const author_urn = record.account_remote_ref.value;
        const result = await this.orm.silent.call("social.post.account", method, [
            [post_id],
            author_urn,
        ]);
        this.env.bus.trigger("SOCIAL:RELOAD_ORGANIZATION", {
            account_id: record.account_id.raw_value,
            post_id: record.remote_ref.raw_value,
        });
        return result;
    },
});
