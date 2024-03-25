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
                    this.broker_type === "whatsapp"
                ) {
                    return "/mail_broker_whatsapp/static/description/icon.png";
                }
                return this._super();
            },
        },
    },
});
