/* Copyright 2016-2017 Jairo Llopis <jairo.llopis@tecnativa.com>
 * License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl). */

odoo.define("website_mass_mailing_name.subscribe", function (require) {
    "use strict";
    require("mass_mailing.website_integration");
    const publicWidget = require("web.public.widget");

    publicWidget.registry.subscribe.include({
        start: function (editable_mode) {
            this.$email = this.$(".js_subscribe_email");
            this.$name = this.$(".js_subscribe_name");
            // Thanks upstream for your @$&#?!! inheritance-ready code.
            // Injecting ajax events to modify behavior of snippet.
            if (this.$name) {
                $(document).ajaxSend($.proxy(this.on_ajax_send, this));
            }
            return this._super(editable_mode);
        },

        _onSubscribeClick: function () {
            // Upstream will not tell user what is wrong with the
            // email validation so this will report with a helping message
            const email_valid = this.$email[0].reportValidity(),
                name_valid = this.$name[0].reportValidity();
            if (!name_valid || !email_valid) {
                return false;
            }
            return this._super.apply(this, arguments);
        },

        on_ajax_send: function (event, jqXHR, ajaxOptions) {
            // Add handlers on correct requests
            if (ajaxOptions.url === "/website_mass_mailing/is_subscriber") {
                jqXHR.done($.proxy(this.disable_name_on_start, this));
            } else if (ajaxOptions.url === "/website_mass_mailing/subscribe") {
                const data = JSON.parse(ajaxOptions.data);
                data.params.email = _.str.sprintf(
                    "%s <%s>",
                    this.$name.val(),
                    data.params.email
                );
                ajaxOptions.data = JSON.stringify(data);
                jqXHR.then($.proxy(this.disable_name_on_subscribe_clic, this));
            }
        },

        disable_name_on_start: function (data) {
            this.$name
                .val(data.result.name || "")
                .prop("disabled", data.result.is_subscriber);
        },

        disable_name_on_subscribe_clic: function (data) {
            this.$name.prop("disabled", Boolean(data.result));
        },
    });
});
