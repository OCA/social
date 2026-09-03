/** @odoo-module **/

import {SocialAccount} from "@social_media_base/components/social_account/social_account.esm";
import {patch} from "@web/core/utils/patch";
import {useBus} from "@web/core/utils/hooks";

/**
 * The card announces the import that runs in the background.
 *
 * Base draws no such notice because base imports nothing: an account it just
 * linked is ready to publish and there is nothing to wait for.
 */
patch(SocialAccount.prototype, {
    /** @override */
    setup() {
        super.setup();
        this.state.syncing = false;
        useBus(this.env.bus, "SOCIAL:SYNCING", async ({detail: data}) => {
            this.state.syncing = data.syncing;
        });
    },

    /** @override */
    _updateStateFromAccounts(socialAccounts) {
        super._updateStateFromAccounts(socialAccounts);
        this.state.syncing = socialAccounts.some((item) => item.pending_initial_sync);
    },
});
