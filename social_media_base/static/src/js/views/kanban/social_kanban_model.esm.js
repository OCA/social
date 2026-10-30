/** @odoo-module **/

import {RelationalModel} from "@web/model/relational_model/relational_model";

export class SocialKanbanModel extends RelationalModel {
    _getDomainSocialAccount() {
        return [];
    }

    /**
     * The fields the account bar of the dashboard draws.
     *
     * Its own method so a module adding to the card asks for its fields in
     * the same read instead of a second one over the same rows.
     *
     * @returns {String[]}
     */
    _accountFields() {
        return [
            "id",
            "name",
            "company_id",
            "media_id",
            "web_url",
            "impression_count",
            "interactions_count",
            "engagement",
            "need_update",
        ];
    }

    async _loadAccounts() {
        return await this.orm.searchRead(
            "social.account",
            this._getDomainSocialAccount(),
            this._accountFields()
        );
    }

    /**
     * Recompute the figures of the cards without asking the social media.
     *
     * Opening the dashboard happens constantly, so it cannot cost a call: the
     * numbers are added up from rows that are already stored.
     *
     * @returns {Promise<Boolean>} whether anything was recomputed.
     */
    async computeDashboardStatistics() {
        return await this.orm.silent.call(
            "social.account",
            "compute_dashboard_statistics",
            [[]]
        );
    }

    /**
     * Ask the social media for the figures again, from the *Update* button.
     *
     * Pressing costs calls, and that is the point: a person asked for it
     * instead of waiting for the cron.
     *
     * @param {Number|null} accountId the account to refresh, all of them when
     *     not given.
     * @returns {Promise<Boolean>} whether anything was refreshed.
     */
    async onUpdatePostsAndStatistics(accountId = null) {
        const account = accountId ? [accountId] : [];
        return await this.orm.silent.call(
            "social.account",
            "refresh_dashboard_statistics",
            [account]
        );
    }
}
