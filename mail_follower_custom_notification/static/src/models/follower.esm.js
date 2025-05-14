/** @odoo-module **/

import {registerPatch} from "@mail/model/model_core";

registerPatch({
    name: "Follower",
    recordMethods: {
        async updateSubtypes() {
            const custom_notifications = Object.fromEntries(
                this.selectedSubtypes
                    .filter((subtype) => subtype.customNotification)
                    .map((subtype) => [subtype.id, subtype.customNotification])
            );
            await this.messaging.rpc({
                model: "mail.followers",
                method: "write",
                args: [
                    [this.id],
                    {mail_follower_custom_notification: custom_notifications},
                ],
            });
            return this._super();
        },
    },
});
