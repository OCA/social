/** @odoo-module **/

import {SocialAccount} from "@social_media_base/components/social_account/social_account.esm";
import {patch} from "@web/core/utils/patch";
import {useBus} from "@web/core/utils/hooks";

/**
 * The card announces what this module imports: the import running in the
 * background, and the publications a check already found and nobody has
 * brought in yet.
 *
 * Base draws neither notice because base imports nothing: an account it just
 * linked is ready to publish and there is nothing to wait for.
 */
patch(SocialAccount.prototype, {
    /** @override */
    setup() {
        super.setup();
        this.state.syncing = false;
        // The flagged accounts themselves and not a boolean, for the same
        // reason base keeps the ones with expired credentials: the notice has
        // to name the account to import.
        this.state.accountsNeedingImport = [];
        useBus(this.env.bus, "SOCIAL:SYNCING", async ({detail: data}) => {
            this.state.syncing = data.syncing;
        });
        useBus(this.env.bus, "SOCIAL:POSTS-NEED-IMPORT", async ({detail: data}) => {
            this._mergeNotifiedAccounts("accountsNeedingImport", data);
        });
    },

    /** @override */
    _updateStateFromAccounts(socialAccounts) {
        super._updateStateFromAccounts(socialAccounts);
        this.state.syncing = socialAccounts.some((item) => item.pending_initial_sync);
        this.state.accountsNeedingImport = this._flaggedAccounts(
            socialAccounts,
            "posts_need_import"
        );
    },

    /** The accounts with publications to import, as one readable list. */
    get accountsNeedingImportLabel() {
        return this._accountsLabel("accountsNeedingImport");
    },
});
