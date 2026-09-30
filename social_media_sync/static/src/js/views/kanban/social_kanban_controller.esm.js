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
     * The third thing the button can answer: it refreshed the figures and
     * found no account with publications to import.
     *
     * Base has only two answers because base imports nothing. Announcing an
     * update that brought publications in, when the only accounts that could
     * have moved were left out on purpose, is what would make the button look
     * broken the next time one of them really is behind.
     *
     * @override
     */
    _updateStatisticsMessage(refreshed) {
        if (refreshed && !this.model.postsImported) {
            return _t("The data was updated. No new publications.");
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
