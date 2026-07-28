/** @odoo-module **/

import {Component} from "@odoo/owl";
import {browser} from "@web/core/browser/browser";

export class SocialAds extends Component {
    static template = "social_media_base.SocialAds";
    static props = {
        socialAds: {type: Object, required: true},
    };

    /**
     * Gets the list of ads.
     *
     * @returns {Object[]} - The list of ads.
     */
    get ads() {
        return this.props.socialAds;
    }

    /**
     * Gets the statistic object of the ads.
     *
     * @returns {Object} - The statistic object of the ads.
     */
    get statistic() {
        return this.props.socialAds.statistic;
    }

    /**
     * Gets the campaign object from the social ads.
     *
     * @returns {Object} - The campaign object of the ads.
     */
    get campaign() {
        return this.props.socialAds.campaign;
    }

    /**
     * Gets the post object from the social ads.
     *
     * @returns {Object} - The post object of the ads.
     */
    get post() {
        return this.props.socialAds.post;
    }

    /**
     * Opens the ad link in a new tab.
     *
     * @returns {void}
     */
    onAdsClick() {
        browser.open(this.ads.url);
    }
}
