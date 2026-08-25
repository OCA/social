/** @odoo-module **/

import {onWillStart, useEffect, useState} from "@odoo/owl";
import {KanbanController} from "@web/views/kanban/kanban_controller";
import {useService} from "@web/core/utils/hooks";

export class SocialAdsKanbanController extends KanbanController {
    /** @override */
    setup() {
        super.setup();
        this.ormService = useService("orm");
        this.actionService = useService("action");
        // Taken from the env: `bus_service` declares `async: true`, which
        // makes `useService` fail on it.
        this.busService = this.env.services.bus_service;
        this.adsState = useState({syncing: false, needUpdate: false});
        // `bus_service.subscribe` has no counterpart in Odoo 17, and this is
        // a view controller, destroyed on every action change: the listener
        // is added and removed by hand instead.
        const handleNotification = ({detail: notifications}) => {
            (notifications || []).forEach(({payload, type}) => {
                if (type === "social_ads_need_update") {
                    this.adsState.needUpdate = Boolean(payload?.need_update);
                }
            });
        };
        useEffect(() => {
            this.busService.addEventListener("notification", handleNotification);
            return () => {
                this.busService.removeEventListener("notification", handleNotification);
            };
        });
        // The bus only carries the notification of a running cron: the flag
        // it stored has to be read back, or the badge is lost on every reload.
        onWillStart(async () => {
            this.adsState.needUpdate = Boolean(
                await this.ormService.call("social.account", "get_ads_need_update", [])
            );
        });
    }

    /** Fetch the ads of every account and show what the social media answered. */
    async onSyncAds() {
        if (this.adsState.syncing) {
            return;
        }
        this.adsState.syncing = true;
        try {
            const action = await this.ormService.call(
                "social.account",
                "action_sync_all_ads_notify",
                []
            );
            this.adsState.needUpdate = false;
            await this.model.load();
            if (action) {
                this.actionService.doAction(action);
            }
        } finally {
            this.adsState.syncing = false;
        }
    }
}
