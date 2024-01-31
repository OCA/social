/** @odoo-module **/

import {registerPatch} from "@mail/model/model_core";

registerPatch({
    name: "Message",
    fields: {
        avatarUrl: {
            compute() {
                if (
                    !this.author &&
                    !this.guestAuthor &&
                    this.gateway_type === "telegram"
                ) {
                    return "/mail_gateway_telegram/static/description/icon.png";
                }
                return this._super();
            },
        },
    },
});
