/* © 2014-2017 Sunflower IT <www.sunflowerweb.nl>*/
odoo.define('mail_edit.thread', function(require) {

    "use strict";

    var thread = require('mail.ChatThread');

    thread.include({
        init: function(){
            this._super.apply(this, arguments);
            this.events['click .o_edit'] = function (event) {
                    var context = {};
                    // save the widget object in a var.
                    var self = this;
                    // Get the action data
                    var message_id = $(event.currentTarget).data('message-id');
                    var do_action = this.do_action;
                    this.rpc("/web/action/load", {
                        "action_id": "mail_edit.mail_edit_action",
                    })
                        .done(function(action) {
                            action.res_id = message_id;
                            action.flags = {
                                action_buttons: true,
                            };
                            action.context = context;
                            do_action(action, {
                                on_close: function () {
                                    // reload view
                                    var parent = self.getParent().getParent().getParent()
                                    if (typeof parent.model !== "undefined"){
                                        parent.reload();
                                    }
                                },
                            });
                        });
            };
        },
    });
});
