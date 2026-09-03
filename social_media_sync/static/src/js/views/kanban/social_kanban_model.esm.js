/** @odoo-module **/

import {SocialKanbanModel} from "@social_media_base/js/views/kanban/social_kanban_model.esm";
import {patch} from "@web/core/utils/patch";

patch(SocialKanbanModel.prototype, {
    /**
     * The same button, which now also imports the publications.
     *
     * The answer stays the one base defines — whether anything was refreshed
     * — because it is what the notification is written from; the imported
     * records reach the cards through the reload the controller does anyway.
     *
     * @override
     */
    async onUpdatePostsAndStatistics(accountId = null, postId = null) {
        const refreshed = await super.onUpdatePostsAndStatistics(accountId);
        const account = accountId ? [accountId] : [];
        await this.orm.silent.call("social.account", "update_posts_statistics", [
            account,
            postId,
            this._getDomainSocialAccount(),
        ]);
        return refreshed;
    },

    /**
     * The flag the card reads to announce the import in the background. Base
     * does not ask for it because base does not have it.
     *
     * @override
     */
    async _loadAccounts() {
        const accounts = await super._loadAccounts();
        if (!accounts.length) {
            return accounts;
        }
        const pending = await this.orm.silent.read(
            "social.account",
            accounts.map((account) => account.id),
            ["pending_initial_sync"]
        );
        const byId = new Map(pending.map((row) => [row.id, row]));
        return accounts.map((account) => ({
            ...account,
            pending_initial_sync: Boolean(byId.get(account.id)?.pending_initial_sync),
        }));
    },
});
