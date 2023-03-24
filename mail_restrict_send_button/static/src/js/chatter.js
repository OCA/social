/** @odoo-module */

import {ChatterTopbar} from "@mail/components/chatter_topbar/chatter_topbar";
import {useService} from "@web/core/utils/hooks";
const {Component, onWillStart} = owl;
import {patch} from "web.utils";

patch(
    ChatterTopbar.prototype,
    "mail/static/src/components/chatter_topbar/chatter_topbar.js",
    {
        setup() {
            this._super();
            this.user = useService("user");
            onWillStart(async () => {
                this.isSendMessage = await this.user.hasGroup(
                    "mail_restrict_send_button.group_show_send_message_button"
                );
            });
        },
    }
);
