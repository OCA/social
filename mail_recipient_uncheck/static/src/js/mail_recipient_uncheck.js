odoo.define('mail_recipient_uncheck', function (require) {
    "use strict";

    var Chatter = require('mail.Chatter');
    var ChatterComposer = require('mail.composer.Chatter');

    Chatter.include({

        _openComposer: function (options) {

            // Boolean checked is harcoded to true here:
            // https://github.com/odoo/odoo/blob/324634da3debefd834b4b5dcf8509da25348324d/addons/mail/static/src/js/chatter.js#L555

            _.each(options.suggested_partners, function (partner) {
                partner.checked = false;
            });

            return this._super.apply(this, arguments);
        },

    });

    ChatterComposer.include({

        // _getCheckedSuggestedPartners filters on input:checked
        // https://github.com/odoo/odoo/blob/324634da3debefd834b4b5dcf8509da25348324d/addons/mail/static/src/js/composers/chatter_composer.js#L177
        // but _checkSuggestedPartners filters again on the original checked boolean here:
        // https://github.com/odoo/odoo/blob/324634da3debefd834b4b5dcf8509da25348324d/addons/mail/static/src/js/composers/chatter_composer.js#L69
        // so we need to set it back to true
        //
        // note that there is a semantic trap:
        // - "checked" first means that the input is selected
        // - then _checkSuggestedPartners "checks" for unknown names/incomplete partners amongst
        //   the selected ones (checked inputs)

        _getCheckedSuggestedPartners: function () {

            var checkedPartners = this._super.apply(this);

            _.each(checkedPartners, function (partner) {
                partner.checked = true;
            });

            return checkedPartners;
        },

    });

});
