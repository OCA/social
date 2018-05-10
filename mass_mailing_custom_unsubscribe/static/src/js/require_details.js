/* Copyright 2016 Jairo Llopis <jairo.llopis@tecnativa.com>
 * License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl). */
odoo.define("mass_mailing_custom_unsubscribe.require_details",
            function (require) {
    "use strict";
    var animation = require("web_editor.snippets.animation");

    animation.registry.mass_mailing_custom_unsubscribe_require_details =
    animation.Class.extend({
        selector: ".js_unsubscription_reason",

        start: function () {
            this.$radio = this.$(":radio");
            this.$details = this.$("[name=details]");
            this.$radio.on("change click", $.proxy(this.toggle, this));
            this.$radio.filter(":checked").trigger("change");
        },

        toggle: function (event) {
            this.$details.prop(
                "required",
                $(event.target).is("[data-details-required]") &&
                $(event.target).is(":visible"));
        },
    });

    return animation.registry.mass_mailing_custom_unsubscribe_require_details;
});
