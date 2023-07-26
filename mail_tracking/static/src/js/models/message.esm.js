/** @odoo-module **/

import {attr, one} from "@mail/model/model_field";
import {registerPatch} from "@mail/model/model_core";

registerPatch({
    name: "Message",
    modelMethods: {
        convertData(data) {
            const data2 = this._super(data);
            if ("partner_trackings" in data) {
                data2.partner_trackings = data.partner_trackings;
            }
            if ("is_failed_message" in data) {
                data2.isFailed = data.is_failed_message;
            }
            return data2;
        },
    },
    recordMethods: {
        hasPartnerTrackings() {
            return _.some(this.__values.get("partner_trackings"));
        },

        hasEmailCc() {
            return _.some(this._emailCc);
        },

        getPartnerTrackings: function () {
            if (!this.hasPartnerTrackings()) {
                return [];
            }
            return this.__values.get("partner_trackings");
        },
    },
    fields: {
        partner_trackings: attr(),
        threads: {
            compute() {
                const threads = this._super();
                if (this.isFailed && this.messaging.failedmsg) {
                    threads.push(this.messaging.failedmsg.thread);
                }
                return threads;
            },
        },
        messagingFailedmsg: one("Mailbox", {
            related: "messaging.failedmsg",
        }),
        isFailed: attr({
            default: false,
        }),
    },
});
