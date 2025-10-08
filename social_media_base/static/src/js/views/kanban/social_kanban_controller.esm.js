/** @odoo-module **/

import {onWillStart, useSubEnv} from "@odoo/owl";
import {useBus, useService} from "@web/core/utils/hooks";
import {KanbanController} from "@web/views/kanban/kanban_controller";
import {SocialAccount} from "@social_media_base/components/social_account/social_account.esm";
import {_t} from "@web/core/l10n/translation";

export class SocialKanbanController extends KanbanController {
    /**
     * @override
     */
    setup() {
        super.setup();
        this.actionService = useService("action");
        this.notificationService = useService("notification");
        this.model.SyncPosts = false;
        onWillStart(async () => {
            if (this.isViewPostNetwork) return;
            this.socialAccounts = await this.model._loadAccounts();
        });
        useSubEnv({
            model: this.model,
        });
        // This bus allows you to reload the account data passed by parameter.
        useBus(this.env.bus, "SOCIAL:RELOAD_ORGANIZATION", async ({detail: data}) => {
            await this._updatePostsAndStatistics(
                data?.account_id ?? null,
                data?.post_id ?? null
            );
        });
    }

    modelsNotShowAccount() {
        return ["social.post", "social.media"];
    }

    /**
     * Checks if the current Kanban view is for the `social.post` model.
     * @type {Boolean}
     */
    get isViewPostNetwork() {
        const models = this.modelsNotShowAccount();
        return models.includes(this.model.config.resModel);
    }

    /**
     * @private
     * @returns {Promise<any>}
     */
    _onAddAccount() {
        return this.actionService.doAction(
            "social_media_base.social_media_act_window_kanban"
        );
    }

    /**
     * Opens the form view of the `social.post` model to create a new post.
     *
     * @private
     * @returns {Promise<any>}
     */
    _onAddPost() {
        return this.actionService.doAction({
            name: _t("New Post"),
            type: "ir.actions.act_window",
            res_model: "social.post",
            views: [[false, "form"]],
        });
    }

    async _updatePostsAndStatistics(account_id = null, post_id = null) {
        const data = await this.model.onUpdatePostsAndStatistics(account_id, post_id);
        this.socialAccounts = JSON.parse(data);
        this.model.load();
    }

    async _onUpdatePostsAndStatistics() {
        this.model.SyncPosts = true;
        await this._updatePostsAndStatistics();
        this.model.SyncPosts = false;
        if (this.socialAccounts.length > 0)
            this.notificationService.add(_t("The data was updated successfully."), {
                type: "info",
            });
        this.env.bus.trigger("SOCIAL:NEED-UPDATE", {
            needUpdate: false,
        });
    }
}

SocialKanbanController.components = {
    ...KanbanController.components,
    SocialAccount,
};
SocialKanbanController.template = "social_media_base.KanbanView";
