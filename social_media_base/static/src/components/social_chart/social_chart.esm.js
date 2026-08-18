/** @odoo-module **/
import {Component, onMounted, useState} from "@odoo/owl";
import {SocialChartAccount} from "@social_media_base/components/social_chart_account/social_chart_account.esm";
import {SocialMediaMixin} from "../../js/app/social_media_mixin.esm";
import {registry} from "@web/core/registry";
import {useService} from "@web/core/utils/hooks";

/**
 * Client action showing the statistics chart of every connected account.
 *
 * Its props are the ones injected by the action service, hence the wildcard.
 */
export class SocialChart extends SocialMediaMixin(Component) {
    static template = "social_media_base.SocialChart";
    static props = ["*"];
    static components = {
        SocialChartAccount,
    };

    /**
     * Sets up the component.
     *
     * The statistics are loaded once the component is mounted: the request
     * hits the social networks, so waiting for it before the first render
     * would leave the action blank instead of showing the loader.
     *
     * @private
     */
    setup() {
        super.setup();
        this.ormService = useService("orm");
        this.social_state = useState({
            statistics: [],
            loaderChart: true,
        });
        onMounted(async () => {
            await this._loadAccountStatistics();
        });
        this.notif_view = "chart";
        this.notificationService = useService("notification");
        this.busService = this.env.services.bus_service;
        this.enableSocialNotifications();
    }

    /**
     * @returns {Object[]} The statistics of every connected account.
     */
    get socialAccountStatistics() {
        return this.social_state.statistics;
    }

    /**
     * Loads the statistics for the social network accounts.
     *
     * @private
     * @returns {Promise<void>}
     */
    async _loadAccountStatistics() {
        this.social_state.loaderChart = true;
        try {
            this.social_state.statistics = await this.ormService.call(
                "social.account",
                "get_chart_account_statistics",
                []
            );
        } finally {
            this.social_state.loaderChart = false;
        }
    }
}

registry.category("actions").add("social_media_chart", SocialChart);
