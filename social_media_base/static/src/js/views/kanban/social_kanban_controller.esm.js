/** @odoo-module **/

import {markup, onWillStart, useState, useSubEnv} from "@odoo/owl";
import {useBus, useService} from "@web/core/utils/hooks";
import {KanbanController} from "@web/views/kanban/kanban_controller";
import {SocialAccount} from "@social_media_base/components/social_account/social_account.esm";
import {_t} from "@web/core/l10n/translation";
import {session} from "@web/session";

export class SocialKanbanController extends KanbanController {
    /** @override */
    setup() {
        super.setup();
        this.actionService = useService("action");
        this.notificationService = useService("notification");
        this.socialState = useState({accounts: [], syncPosts: false});
        onWillStart(() => {
            // Not awaited on purpose: the kanban must paint its records without
            // waiting for the account bar data.
            this._loadSocialAccounts();
        });
        useSubEnv({
            model: this.model,
        });
        useBus(this.env.bus, "SOCIAL:POSTS-UPDATED", async ({detail: payload}) => {
            await this._reloadPostsAndStatistics(payload);
        });
    }

    modelsNotShowAccount() {
        return ["social.post", "social.media"];
    }

    get isAccountPanelHidden() {
        const models = this.modelsNotShowAccount();
        return models.includes(this.model.config.resModel);
    }

    async _loadSocialAccounts() {
        if (this.isAccountPanelHidden) return;
        // Recomputed before being read, not after: the figures of the cards
        // come from those rows, so reading first would draw what was already
        // on screen. It asks nothing of the social media, so it is free.
        await this.model.computeDashboardStatistics();
        this.socialState.accounts = await this.model._loadAccounts();
    }

    _onAddAccount() {
        return this.actionService.doAction("social_media_base.social_media_action");
    }

    _onAddPost() {
        return this.actionService.doAction({
            name: _t("New Post"),
            type: "ir.actions.act_window",
            res_model: "social.post",
            views: [[false, "form"]],
        });
    }

    async _reloadPostsAndStatistics(payload = {}) {
        if (this.isAccountPanelHidden) return;
        this.socialState.accounts = await this.model._loadAccounts();
        await this.model.load();
        this.socialState.syncPosts = false;
        this.env.bus.trigger("SOCIAL:SYNCING", {syncing: false});
        this.notificationService.add(
            payload.message
                ? markup(payload.message)
                : _t("The posts of the account were updated."),
            {type: payload.message_type || "info"}
        );
    }

    async _updatePostsAndStatistics(accountId = null, postId = null) {
        const refreshed = await this.model.onUpdatePostsAndStatistics(
            accountId,
            postId
        );
        this.socialState.accounts = await this.model._loadAccounts();
        this.model.load();
        return refreshed;
    }

    async _onUpdatePostsAndStatistics() {
        this.socialState.syncPosts = true;
        const refreshed = await this._updatePostsAndStatistics();
        if (!session.social_error) {
            // Saying nothing came back is more useful than announcing an
            // update that did not happen: a social media reporting no figures
            // by day has nothing to bring in.
            this.notificationService.add(
                refreshed
                    ? _t("The data was updated successfully.")
                    : _t("There are no statistics to bring in for these accounts."),
                {type: "info"}
            );
        }
        this.socialState.syncPosts = false;
        session.social_error = false;
    }
}

SocialKanbanController.components = {
    ...KanbanController.components,
    SocialAccount,
};
SocialKanbanController.template = "social_media_base.KanbanView";
