import {Component, onWillStart} from "@odoo/owl";
import {SocialChartAccount} from "@social_media_base/components/social_chart_account/social_chart_account.esm";
import {SocialMediaMixin} from "../../js/app/social_media_mixin.esm";
import {registry} from "@web/core/registry";
import {useService} from "@web/core/utils/hooks";

export class SocialChart extends SocialMediaMixin(Component) {
    static template = "social_media_base.SocialChart";
    static components = {
        SocialChartAccount,
    };

    /**
     * Sets up the component.
     *
     * @private
     */
    setup() {
        super.setup();
        this.ormService = useService("orm");
        this.socialAccountStatistics = [];
        onWillStart(async () => {
            await this._loadAccountStatistics();
        });
        this.notif_view = "chart";
        this.notificationService = useService("notification");
        this.busService = this.env.services.bus_service;
        this.enableSocialNotifications();
    }

    /**
     * Loads the statistics for the social network accounts.
     *
     * @private
     * @returns {Promise<void>}
     */
    async _loadAccountStatistics() {
        this.socialAccountStatistics = await this.ormService.call(
            "social.account",
            "get_chart_account_statistics",
            [[]]
        );
    }
}

registry.category("actions").add("social_media_chart", SocialChart);