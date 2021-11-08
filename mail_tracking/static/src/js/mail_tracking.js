odoo.define("mail_tracking/static/src/js/mail_tracking.js", function (require) {
    "use strict";

    const {
        registerClassPatchModel,
        registerFieldPatchModel,
        registerInstancePatchModel,
    } = require("mail/static/src/model/model_core.js");
    const {attr} = require("mail/static/src/model/model_field.js");

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
});
