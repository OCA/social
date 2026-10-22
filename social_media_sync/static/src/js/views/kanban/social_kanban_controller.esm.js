/** @odoo-module **/

import {SocialKanbanController} from "@social_media_base/js/views/kanban/social_kanban_controller.esm";
import {_t} from "@web/core/l10n/translation";
import {patch} from "@web/core/utils/patch";
import {useBus} from "@web/core/utils/hooks";

patch(SocialKanbanController.prototype, {
    /** @override */
    setup() {
        super.setup();
        // Only a comment and a reaction raise it, and answering it means
        // importing the publication again, so both ends of the event are this
        // module's.
        useBus(this.env.bus, "SOCIAL:RELOAD_ORGANIZATION", async ({detail: data}) => {
            await this._updatePostsAndStatistics(
                data?.account_id ?? null,
                data?.post_id ?? null
            );
        });
    },

    /**
     * What the button answers once the import reported what it read.
     *
     * Base has only two answers because base imports nothing. An account
     * whose social media was read is an update, whatever the figures said,
     * and the notice tells a read that brought publications in from one that
     * found none: announcing publications that did not come is what would
     * make the button look broken the next time an account really is behind.
     * When no account was read, the figures are all there is to word, and
     * base words them.
     *
     * @override
     */
    _updateStatisticsMessage(refreshed) {
        const report = this.model.postsReport || {};
        if (report.read) {
            return report.imported
                ? _t("The data was updated. New publications were imported.")
                : _t("The data was updated. No new publications.");
        }
        return super._updateStatisticsMessage(refreshed);
    },

    /** @override */
    async _loadSocialAccounts() {
        await super._loadSocialAccounts();
        this.socialState.syncPosts = this.socialState.accounts.some(
            (account) => account.pending_initial_sync
        );
    },
});
