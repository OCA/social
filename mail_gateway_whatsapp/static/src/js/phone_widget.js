/** ********************************************************************************
    Copyright 2022 Creu Blanca
    License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).
 **********************************************************************************/

odoo.define("mail_broker_whatsapp.phone_widget", function(require) {
    "use strict";
    var basic_fields = require("web.basic_fields");
    var core = require("web.core");
    var session = require("web.session");

    var _t = core._t;
    basic_fields.FieldPhone.include({
        /**
         * Add a button to call the composer wizard
         *
         * @override
         * @private
         */
        _renderReadonly: function() {
            var def = this._super.apply(this, arguments);
            if (this.nodeOptions.enable_sms) {
                var $composerButton = $("<a>", {
                    title: _t("Send Whatsapp Message"),
                    href: "",
                    class: "ml-3 d-inline-flex align-items-center o_field_phone_sms",
                });
                $composerButton.prepend($("<i>", {class: "fa fa-whatsapp"}));
                $composerButton.on("click", this._onClickWhatsapp.bind(this));
                this.$el.append($composerButton);
            }

            return def;
        },
        _onClickWhatsapp: function(ev) {
            ev.preventDefault();

            var context = session.user_context;
            context = _.extend({}, context, {
                default_res_model: this.model,
                default_res_id: parseInt(this.res_id, 10),
                default_number_field_name: this.name,
                default_composition_mode: "comment",
            });
            var self = this;
            return this.do_action(
                {
                    title: _t("Send Whatsapp Message"),
                    type: "ir.actions.act_window",
                    res_model: "whatsapp.composer",
                    target: "new",
                    views: [[false, "form"]],
                    context: context,
                },
                {
                    on_close: function() {
                        self.trigger_up("reload");
                    },
                }
            );
        },
    });
});
