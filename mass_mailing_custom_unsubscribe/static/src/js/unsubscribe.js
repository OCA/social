/* Copyright 2016 Jairo Llopis <jairo.llopis@tecnativa.com>
 * License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl). */

/* TODO This JS module replaces core AJAX submission because it is impossible
 * to extend it as it is currently designed. Most of this code has been
 * upstreamed in https://github.com/odoo/odoo/pull/14386, so we should extend
 * that when it gets merged, and remove most of this file. */
odoo.define("mass_mailing_custom_unsubscribe.unsubscribe", function (require) {
    "use strict";
    var core = require("web.core");
    var ajax = require("web.ajax");
    var animation = require("web_editor.snippets.animation");
    var _t = core._t;

    animation.registry.mass_mailing_unsubscribe =
    animation.Class.extend({
        selector: "#unsubscribe_form",
        start: function () {
            this.controller = '/mail/mailing/unsubscribe';
            this.$alert = this.$(".alert");
            this.$email = this.$("input[name='email']");
            this.$contacts = this.$("input[name='contact_ids']");
            this.$mailing_id = this.$("input[name='mailing_id']");
            this.$token = this.$("input[name='token']");
            this.$res_id = this.$("input[name='res_id']");
            this.$reasons = this.$(".js_unsubscription_reason");
            this.$details = this.$reasons.find("[name='details']")
            this.$el.on("submit", $.proxy(this.submit, this));
            this.$contacts.on("change", $.proxy(this.toggle_reasons, this));
            this.toggle_reasons();
        },

        // Helper to get list ids, to use in this.$contacts.map()
        int_val: function (index, element) {
            return parseInt($(element).val(), 10);
        },

        // Get a filtered array of integer IDs of matching lists
        contact_ids: function (checked) {
            var filter = checked ? ":checked" : ":not(:checked)";
            return this.$contacts.filter(filter).map(this.int_val).get();
        },

        // Display reasons form only if there are unsubscriptions
        toggle_reasons: function () {
            // Find contacts that were checked and now are unchecked
            var $disabled = this.$contacts.filter(function () {
                var $this = $(this);
                return !$this.prop("checked") && $this.attr("checked");
            });
            // Hide reasons form if you are only subscribing
            this.$reasons.toggleClass("hidden", !$disabled.length);
            var $radios = this.$reasons.find(":radio");
            if (this.$reasons.is(":hidden")) {
                // Uncheck chosen reason
                $radios.prop("checked", false)
                // Unrequire specifying a reason
                .prop("required", false)
                // Remove possible constraints for details
                .trigger("change");
            } else {
                // Require specifying a reason
                $radios.prop("required", true);
            }
        },

        // Get values to send
        values: function () {
            var result = {
                email: this.$email.val(),
                mailing_id: parseInt(this.$mailing_id.val(), 10),
                opt_in_ids: this.contact_ids(true),
                opt_out_ids: this.contact_ids(false),
                res_id: parseInt(this.$res_id.val(), 10),
                token: this.$token.val(),
            };
            // Only send reason and details if an unsubscription was found
            if (this.$reasons.is(":visible")) {
                result.reason_id = parseInt(
                    this.$reasons.find("[name='reason_id']:checked").val(),
                    10
                );
                result.details = this.$details.val();
            }
            return result;
        },

        // Submit by ajax
        submit: function (event) {
            event.preventDefault();
            return ajax.jsonRpc(this.controller, "call", this.values())
            .done($.proxy(this.success, this))
            .fail($.proxy(this.failure, this));
        },

        // When you successfully saved the new subscriptions status
        success: function () {
            this.$alert
            .html(_t('Your changes have been saved.'))
            .removeClass("alert-info alert-warning")
            .addClass("alert-success");

            // Store checked status, to enable further changes
            this.$contacts.each(function () {
                var $this = $(this);
                $this.attr("checked", $this.prop("checked"));
            });
            this.toggle_reasons();
        },

        // When you fail to save the new subscriptions status
        failure: function () {
            this.$alert
            .html(_t('Your changes have not been saved, try again later.'))
            .removeClass("alert-info alert-success")
            .addClass("alert-warning");
        },
    });

    return animation.registry.mass_mailing_unsubscribe;
});
