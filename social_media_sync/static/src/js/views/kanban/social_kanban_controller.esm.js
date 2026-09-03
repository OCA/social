/** @odoo-module **/

import {SocialKanbanController} from "@social_media_base/js/views/kanban/social_kanban_controller.esm";
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

    /** @override */
    async _loadSocialAccounts() {
        await super._loadSocialAccounts();
        this.socialState.syncPosts = this.socialState.accounts.some(
            (account) => account.pending_initial_sync
        );
    },
});
