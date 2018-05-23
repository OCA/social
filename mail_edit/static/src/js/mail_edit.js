/* © 2014-2017 Sunflower IT <www.sunflowerweb.nl>*/

"use strict";
openerp.mail_edit = function (instance) {
    var _t = instance.web._t;
    instance.mail.ThreadMessage.include({
        bind_events: function () {
            this._super.apply(this, arguments);
            this.$('.oe_edit').on('click', this.on_message_edit);
            this.$('.oe_delete').on('click', this.on_message_delete);
        },

        on_message_edit: function () {
            var context = {};

            // save the widget object in a var.
            var self = this;

            // Get the action data
            var do_action = this.do_action;

            this.rpc("/web/action/load", {
                "action_id": "mail_edit.mail_edit_action",
            })
            .done(function(action) {
                action.res_id = self.id;
                action.flags = {
                    action_buttons: true,
                };
                action.context = context;
                do_action(action, {
                    on_close: function () {
                        // reload view
                        var parent = self.getParent().getParent().getParent().getParent()
                        if (typeof parent.model !== "undefined"){
                            parent.reload();
                        }
                    },
                });
            });
        }
    });

    instance.mail.MessageCommon.include({
                init: function (parent, datasets, options) {
                    this._super(parent, datasets, options);
                    this.is_superuser = datasets.is_superuser || false;
                }
    });
};
