/** @odoo-module **/

import {Component, onWillStart, useState} from "@odoo/owl";
import {useBus, useService} from "@web/core/utils/hooks";
import {formatFloat} from "@web/views/fields/formatters";

export class SocialAccount extends Component {
    static template = "social_media_base.SocialAccount";
    static props = {
        socialAccounts: {type: Array},
    };

    setup() {
        super.setup();
        this.orm = useService("dialog");
        this.state = useState({
            needUpdate: false,
        });
        onWillStart(async () => {
            this.state.needUpdate =
                this.props.socialAccounts.filter((item) => item.need_update).length > 0;
        });
        useBus(this.env.bus, "SOCIAL:NEED-UPDATE", async ({detail: data}) => {
            this.state.needUpdate = data.needUpdate;
        });
    }

    /**
     * Formats the engagement value with two decimal places, avoiding
     * floating point representation artifacts (e.g. 1.1500000000000001).
     *
     * @param {Number} value - The engagement value to format.
     * @returns {String} The formatted value.
     */
    formatEngagement(value) {
        return formatFloat(value || 0, {digits: [16, 2]});
    }
}
