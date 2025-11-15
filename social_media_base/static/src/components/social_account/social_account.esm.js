/** @odoo-module **/

import {Component, onWillStart, useState} from "@odoo/owl";
import {useBus, useService} from "@web/core/utils/hooks";

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
}
