odoo.define("mail_allow_portal_internal_note.composer", function (require) {
    "use strict";

    var composer = require("portal.composer");
    const ajax = require("web.ajax");

    composer.PortalComposer.include({
        xmlDependencies: composer.PortalComposer.prototype.xmlDependencies.concat([
            "/mail_allow_portal_internal_note/static/src/xml/mail_portal_template.xml",
        ]),
        events: _.extend({}, composer.PortalComposer.prototype.events, {
            "click .o_portal_chatter_log_note_btn": "_onLogNoteButtonClick",
        }),
        start: async function () {
            var rec = this._super();
            this.$loginput = this.$(".o_portal_chatter_is_log_note");
            if (this.options && this.options.res_id && this.options.res_model) {
                var is_portal_see = await ajax.jsonRpc(
                    "/can_portal_see_internal_messages",
                    "call",
                    {
                        res_model: this.options.res_model,
                        res_id: this.options.res_id,
                    }
                );
                if (!is_portal_see) {
                    this.$(".o_portal_chatter_log_note_btn").addClass("o_hidden");
                }
            }
            return rec;
        },
        _onLogNoteButtonClick: function () {
            this.$loginput.val("True");
            this.$sendButton.click();
        },
    });
});
