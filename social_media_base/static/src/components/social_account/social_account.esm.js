/** @odoo-module **/

import {Component, onWillStart, onWillUpdateProps, useState} from "@odoo/owl";
import {formatFloat} from "@web/views/fields/formatters";
import {useBus} from "@web/core/utils/hooks";

export class SocialAccount extends Component {
    static template = "social_media_base.SocialAccount";
    static props = {
        socialAccounts: {type: Array},
    };

    setup() {
        super.setup();
        this.state = useState({
            // The flagged accounts themselves, not a boolean: the warning has
            // to name the account to act on, and a user may be responsible for
            // several on several social media.
            accountsNeedingUpdate: [],
        });
        onWillStart(() => this._updateStateFromAccounts(this.props.socialAccounts));
        // The accounts are loaded after the first paint, so the state has to be
        // refreshed when they finally reach the component.
        onWillUpdateProps((nextProps) =>
            this._updateStateFromAccounts(nextProps.socialAccounts)
        );
        useBus(this.env.bus, "SOCIAL:NEED-UPDATE", async ({detail: data}) => {
            this._mergeNotifiedAccounts("accountsNeedingUpdate", data);
        });
    }

    _updateStateFromAccounts(socialAccounts) {
        this.state.accountsNeedingUpdate = this._flaggedAccounts(
            socialAccounts,
            "need_update"
        );
    }

    /**
     * Merge into a notice the accounts a bus message names.
     *
     * The message only speaks of the accounts it names: a user may be
     * responsible for several, and one of them being authorized again — or
     * imported — says nothing about the others.
     *
     * @param {String} key entry of the state holding the notice.
     * @param {Object} data payload of the bus message.
     */
    _mergeNotifiedAccounts(key, data) {
        const named = data.accounts ?? [];
        const kept = this.state[key].filter(
            (item) => !named.some((account) => account.id === item.id)
        );
        this.state[key] = data.needUpdate ? kept.concat(named) : kept;
    }

    /**
     * The accounts of the bar whose flag is set, as entries of a notice.
     *
     * @param {Object[]} socialAccounts the accounts the bar draws.
     * @param {String} flag field the notice is raised on.
     * @returns {Object[]}
     */
    _flaggedAccounts(socialAccounts, flag) {
        return socialAccounts
            .filter((item) => item[flag])
            .map((item) => ({
                id: item.id,
                name: item.name,
                media: item.media_id ? item.media_id[1] : "",
            }));
    }

    /**
     * The accounts of a notice as one readable list.
     *
     * A single warning naming all of them instead of one warning per account:
     * a user responsible for a dozen accounts would otherwise get a dozen
     * banners pushing the dashboard off the screen.
     *
     * @param {String} key entry of the state holding the notice.
     * @returns {String}
     */
    _accountsLabel(key) {
        return this.state[key].map((item) => `[${item.media}] ${item.name}`).join(", ");
    }

    /** The accounts with expired credentials, as one readable list. */
    get accountsNeedingUpdateLabel() {
        return this._accountsLabel("accountsNeedingUpdate");
    }

    /**
     * Render the engagement of an account as a percentage.
     *
     * The rate is stored as a ratio, on the same scale as the daily series.
     * This is the only place that knows the scale it is shown in.
     *
     * @param {Number} value
     * @returns {String}
     */
    formatEngagement(value) {
        return `${formatFloat((value || 0) * 100, {digits: [16, 2]})} %`;
    }
}
