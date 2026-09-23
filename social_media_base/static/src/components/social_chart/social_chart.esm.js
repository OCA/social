import {Component, onWillStart} from "@odoo/owl";
import {SocialChartAccount} from "@social_media_base/components/social_chart_account/social_chart_account.esm";
import {registry} from "@web/core/registry";
import {useService} from "@web/core/utils/hooks";

export class SocialChart extends Component {
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
