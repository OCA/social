/** @odoo-module **/

import {Component, onWillStart, useState} from "@odoo/owl";
import {ControlPanel} from "@web/search/control_panel/control_panel";
import {SocialAds} from "../social_ads/social_ads.esm";
import {SocialFilter} from "../social_filter/social_filter.esm";
import {registry} from "@web/core/registry";
import {useService} from "@web/core/utils/hooks";

const {DateTime} = luxon;

export class SocialAdsAccount extends Component {
    static template = "social_media_base.SocialAdsAccount";
    static components = {
        ControlPanel,
        SocialAds,
        SocialFilter,
    };

    /**
     * Initializes the component by setting up services and initializing state.
     *
     * This method sets up the ORM and notification services, and initializes
     * the state variables for social ads, campaigns, and posts. It also
     * triggers the loading of ad accounts before the component starts.
     */
    setup() {
        this.ormService = useService("orm");
        this.notification = useService("notification");
        this.socialAdsAccount = [];
        this.campaigns = [];
        this.posts = [];
        this.social_state = useState({
            socialAds: [],
            loaderAds: false,
        });
        onWillStart(async () => {
            await this._loadAdsAccount();
        });
    }

    filter_ads(item, startDate, endDate, val_search) {
        const created = DateTime.fromFormat(item.created, "dd/MM/yyyy");
        const start_date = DateTime.fromFormat(startDate, "yyyy-MM-dd");
        const end_date = DateTime.fromFormat(endDate, "yyyy-MM-dd");
        return (
            (start_date ? created >= start_date : false) &&
            (end_date ? created <= end_date : false) &&
            (val_search
                ? (item.campaign.name
                      ? item.campaign.name.includes(val_search)
                      : false) ||
                  (item.post.name ? item.post.name.includes(val_search) : false) ||
                  item.status.includes(val_search)
                : true)
        );
    }

    onFilterAds({startDate, endDate, val_search}) {
        if (val_search || startDate || endDate) {
            this.social_state.socialAds = this.socialAdsAccount.ads.filter((item) => {
                return this.filter_ads(item, startDate, endDate, val_search);
            });
        } else {
            this.clearFilter();
        }
    }

    /**
     * Clears the filter and displays all ads again.
     *
     * When called, this method resets the `socialAds` state to the original
     * list of ads retrieved from the server, effectively clearing any
     * filtering criteria.
     */
    clearFilter() {
        this.social_state.socialAds = this.socialAdsAccount.ads;
    }

    /**
     * Gets the ads after applying the filter criteria.
     *
     * @returns {Object[]} - The ads after applying the filter criteria.
     */
    get ads() {
        return this.social_state.socialAds;
    }

    /**
     * Loads all ads again from the server.
     *
     * This method is triggered by the "Sync ads" button and is used to
     * reload all ads from the server. It will clear any filtering criteria
     * and display all ads again.
     *
     * @returns {Promise<void>}
     */
    async onUpdateAllAds() {
        await this._loadAdsAccount();
    }

    /**
     * Loads all ads from the server.
     *
     * This method is called when the user clicks on the "Sync ads" button.
     * It will clear any filtering criteria, set the `loaderAds` state to
     * `true`, and load all ads from the server. After loading the ads,
     * it sets the `loaderAds` state to `false` and updates the component's
     * state with the retrieved ads.
     *
     * @returns {Promise<void>}
     */
    async _loadAdsAccount() {
        this.social_state.loaderAds = true;
        const adsAccount = await this.ormService.call(
            "social.account",
            "load_ads_accounts",
            [[]]
        );
        this.socialAdsAccount = adsAccount;
        this.social_state.socialAds = adsAccount.ads;
        this.campaigns = adsAccount.campaigns;
        this.posts = adsAccount.posts;
        this.social_state.loaderAds = false;
    }
}

registry.category("actions").add("social_ads_account", SocialAdsAccount);
