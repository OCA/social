/* Copyright 2016-2017 Jairo Llopis <jairo.llopis@tecnativa.com>
 * License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl). */

odoo.define("website_mass_mailing_name.subscribe", function (require) {
    "use strict";
    require("mass_mailing.website_integration");
    var animation = require("web_editor.snippets.animation");

    animation.registry.subscribe.include({
        start: function(editable_mode) {
            this.$email = this.$target.find(".js_subscribe_email");
            this.$name = this.$target.find(".js_subscribe_name");
            // Thanks upstream for your @$&#?!! inheritance-ready code.
            // Injecting ajax events to modify behavior of snippet.
            if (this.$name) {
                $(document).ajaxSend($.proxy(this.on_ajax_send, this));
            }
            return this._super(editable_mode);
        },

        on_click: function() {
            var email_error = !this.$email.val().match(/.+@.+/),
                name_error = this.$name.length && !this.$name.val(),
                values = {
                    "list_id": this.$target.data('list-id'),
                    "email": this.$email.val(),
                };
            // Stop on error
            if (email_error || name_error) {
                this.$target.addClass("has-error")
                return false;
            }
            return this._super.apply(this, arguments);
        },

        on_ajax_send: function(event, jqXHR, ajaxOptions) {
            // Add handlers on correct requests
            if (ajaxOptions.url == "/website_mass_mailing/is_subscriber") {
                jqXHR.done($.proxy(this.on_start, this));
            } else if (ajaxOptions.url == "/website_mass_mailing/subscribe") {
                var data = JSON.parse(ajaxOptions.data);
                data.params.email = _.str.sprintf(
                    "%s <%s>",
                    this.$name.val(),
                    data.params.email
                );
                ajaxOptions.data = JSON.stringify(data);
            }
        },

        on_start: function(data) {
            this.$name.val(data.result.name)
            .attr(
                "disabled",
                Boolean(data.result.is_subscriber && data.result.name.length)
            );
        },
    });
});
