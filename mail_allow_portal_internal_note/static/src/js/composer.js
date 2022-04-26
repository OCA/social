odoo.define("mail_allow_portal_internal_note.composer", function (require) {
    "use strict";

    var composer = require("portal.composer");
    composer.PortalComposer.include({
        xmlDependencies: composer.PortalComposer.prototype.xmlDependencies.concat([
            "/mail_allow_portal_internal_note/static/src/xml/mail_portal_template.xml",
        ]),
        events: _.extend({}, composer.PortalComposer.prototype.events, {
            "click .o_portal_chatter_log_note_btn": "_onLogNoteButtonClick",
        }),
        start: function () {
            this.$loginput = this.$(".o_portal_chatter_is_log_note");
            return this._super();
        },
        _onLogNoteButtonClick: function () {
            this.$loginput.val("True");
            this.$sendButton.click();
        },
    });
});
