/** @odoo-module **/

import { registerPatch } from '@mail/model/model_core';
import {attr} from "@mail/model/model_field";

registerPatch({
    name: 'Message',
    modelMethods: {
        /**
         * @override
         */
        convertData(data) {
            const res = this._super(data);
            if ('partner_trackings' in data) {
                res.partner_trackings = data.partner_trackings;
            }
            return res;
        },
    },
    fields: {
        partner_trackings: attr({
            default: false,
        }),
    },
    recordMethods: {
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
});
