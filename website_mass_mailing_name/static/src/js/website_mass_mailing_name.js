/* © 2016 Jairo Llopis <jairo.llopis@tecnativa.com>
 * License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl). */

"use strict";
(function ($) {
    openerp.website.snippet.animationRegistry.subscribe.include({
        start: function(editable_mode) {
            var self = this;
            self.$email = self.$target.find(".js_subscribe_email");
            self.$name = self.$target.find(".js_subscribe_name");

            // Thanks upstream for your @$&#?!! inheritance-ready code.
            // Injecting ajax events to modify behavior of snippet.
            if (self.$name) {
                $(document).ajaxSend(function(event, jqXHR, ajaxOptions) {
                    return self.on_ajax_send(event, jqXHR, ajaxOptions);
                });
            }

            return self._super(editable_mode);
        },
        on_click: function() {
            var self = this,
                email_error = !self.$email.val().match(/.+@.+/),
                name_error = self.$name.length && !self.$name.val(),
                values = {
                    "list_id": self.$target.data('list-id'),
                    "email": self.$email.val(),
                };

            // Stop on error
            if (email_error || name_error) {
                self.$target.addClass("has-error")
                return false;
            }
            return self._super();
        },
        on_ajax_send: function(event, jqXHR, ajaxOptions) {
            var self = this;

            // Add handlers on correct requests
            if (ajaxOptions.url == "/website_mass_mailing/is_subscriber") {
                jqXHR.then(function(data) {
                    return self.on_start(data);
                });
            } else if (ajaxOptions.url == "/website_mass_mailing/subscribe") {
                var data = JSON.parse(ajaxOptions.data);
                data.params.email =
                    self.$name.val() + " <" + data.params.email + ">";
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
})(jQuery);
