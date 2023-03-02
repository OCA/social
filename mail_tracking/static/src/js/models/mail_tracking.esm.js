/** @odoo-module **/

import {attr} from "@mail/model/model_field";
import {registerPatch} from "@mail/model/model_core";

registerPatch({
    name: "Message",
    modelMethods: {
        convertData(data) {
            const data2 = this._super(data);
            if ("partner_trackings" in data) {
                console.log(data.partner_trackings);
                data2.partner_trackings = data.partner_trackings;
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
    },
});
