/** @odoo-module **/

import {
    registerClassPatchModel,
    registerFieldPatchModel,
    registerInstancePatchModel,
} from "@mail/model/model_core";
import {attr} from "@mail/model/model_field";

registerClassPatchModel(
    "mail.message",
    "mail_tracking/static/src/js/mail_tracking.js",
    {
        convertData(data) {
            const data2 = this._super(data);
            if ("partner_trackings" in data) {
                data2.partner_trackings = data.partner_trackings;
            }
            return data2;
        },
    }
);

registerFieldPatchModel(
    "mail.message",
    "mail_tracking/static/src/js/mail_tracking.js",
    {
        partner_trackings: attr(),
    }
);

registerInstancePatchModel(
    "mail.model",
    "mail_tracking/static/src/js/mail_tracking.js",
    {
        hasPartnerTrackings() {
            return _.some(this.__values.partner_trackings);
        },

        hasEmailCc() {
            return _.some(this._emailCc);
        },

        getPartnerTrackings: function () {
            if (!this.hasPartnerTrackings()) {
                return [];
            }
            return this.__values.partner_trackings;
        },
    }
);
