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
                    this.broker_type === "telegram"
                ) {
                    return "/mail_broker_telegram/static/description/icon.png";
                }
                return this._super();
            },
        },
    },
});
