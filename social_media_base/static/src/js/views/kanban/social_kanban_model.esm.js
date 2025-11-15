/** @odoo-module **/

import {RelationalModel} from "@web/model/relational_model/relational_model";

export class SocialKanbanModel extends RelationalModel {
    _get_domain_social_account() {
        return [];
    }

    _get_select_fields(media = null) {
        var fields = ["id", "name"];
        if (media) {
            fields.push("media_id");
        }
        return fields;
    }

    /**
     * @returns {Promise<Object[]>} a promise that resolves with
     * an array of objects representing the social network accounts.
     * Each object has the following properties:
     * - id
     * - name
     * - company_id
     * - media_id
     * - account_url
     * - impression_count
     * - interactions_count
     * - engagement
     * - need_update
     */
    async _loadAccounts() {
        return await this.orm.searchRead(
            "social.account",
            this._get_domain_social_account(),
            [
                "id",
                "name",
                "company_id",
                "media_id",
                "account_url",
                "impression_count",
                "interactions_count",
                "engagement",
                "need_update",
            ]
        );
    }

    /**
     * @returns {Promise<Object[]>} a promise that resolves with
     * an array of objects with `id` and `name` properties, representing
     * the social network accounts that are not yet synchronized.
     *
     * @param {String} media - The media type to filter by.
     */
    async _loadAccountsBasic(media = null) {
        if (media)
            return await this.orm.searchRead(
                "social.account",
                [["media_type", "=", media]],
                this._get_select_fields(media)
            );
        return [];
    }

    async onUpdatePostsAndStatistics(account_id = null, post_id = null) {
        const account = account_id ? [account_id] : [];
        return await this.orm.silent.call("social.account", "update_posts_statistics", [
            account,
            post_id,
            this._get_domain_social_account(),
        ]);
    }

    /**
     * @param {Object} record a record of a social network post account
     * @description
     * Likes the given post on the social network. The post is identified by the
     * `id` field of the `record` argument. The method silently calls the "like_post"
     * method on the "social.post.account" model, passing the `record` argument
     * and no other arguments.
     */
    onLikePost(record) {
        if (!record) return;
        return;
    }
}
