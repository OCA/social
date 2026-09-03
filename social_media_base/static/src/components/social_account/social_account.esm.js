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
            // The message only speaks of the accounts it names: a user may be
            // responsible for several, and one of them being authorized again
            // says nothing about the others.
            const named = data.accounts ?? [];
            const kept = this.state.accountsNeedingUpdate.filter(
                (item) => !named.some((account) => account.id === item.id)
            );
            this.state.accountsNeedingUpdate = data.needUpdate
                ? kept.concat(named)
                : kept;
        });
    }

    _updateStateFromAccounts(socialAccounts) {
        this.state.accountsNeedingUpdate = socialAccounts
            .filter((item) => item.need_update)
            .map((item) => ({
                id: item.id,
                name: item.name,
                media: item.media_id ? item.media_id[1] : "",
            }));
    }

    /**
     * The flagged accounts as one readable list.
     *
     * A single warning naming all of them instead of one warning per account:
     * a user responsible for a dozen accounts would otherwise get a dozen
     * banners pushing the dashboard off the screen.
     *
     * @returns {String}
     */
    get accountsNeedingUpdateLabel() {
        return this.state.accountsNeedingUpdate
            .map((item) => `[${item.media}] ${item.name}`)
            .join(", ");
    }

    formatEngagement(value) {
        return formatFloat(value || 0, {digits: [16, 2]});
    }
}
