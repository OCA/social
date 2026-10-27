/** @odoo-module **/

import {SocialKanbanModel} from "@social_media_base/js/views/kanban/social_kanban_model.esm";
import {patch} from "@web/core/utils/patch";

patch(SocialKanbanModel.prototype, {
    /**
     * The social media of each account, so the controller can tell whether
     * the import of *Update* read an X timeline.
     *
     * @override
     */
    _accountFields() {
        return [...super._accountFields(), "media_type"];
    },

    /** @override */
    async onLikePost(record) {
        if (record?.media_type?.raw_value !== "x") {
            return super.onLikePost(...arguments);
        }
        return await this._reactXPost(record, "action_like_post");
    },

    /** @override */
    async onUnlikePost(record) {
        if (record?.media_type?.raw_value !== "x") {
            return super.onUnlikePost(...arguments);
        }
        return await this._reactXPost(record, "action_unlike_post");
    },

    /**
     * Send the like of the account and redraw what the card shows.
     *
     * The like is given as the account the publication belongs to, which the
     * server reads from its own token, so nothing names the actor here.
     *
     * @param {Object} record the publication the entry was pressed on.
     * @param {String} method the method of `social.post.account` to call.
     * @returns {Promise<Object>} what the connector answered.
     */
    async _reactXPost(record, method) {
        const result = await this.orm.silent.call("social.post.account", method, [
            [record.id.raw_value],
        ]);
        this.env.bus.trigger("SOCIAL:RELOAD_ORGANIZATION", {
            account_id: record.account_id.raw_value,
            post_id: record.remote_ref.raw_value,
        });
        return result;
    },
});
