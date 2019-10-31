odoo.define('mail_edit.ChatThread', function (require) {
"use strict";

    var Thread = require('web.Widget');
    var chat_manager = require('mail.chat_manager');

    chat_manager._make_message_super = chat_manager.make_message;
    chat_manager.make_message = function(data) {
        var msg = chat_manager._make_message_super(data);
        msg.edited = data.edited || false;
        return msg;
    };

    Thread.include({
        events: _.extend({}, Thread.prototype.events, {
            "click .o_thread_edited_label": function (event) {
                var message_id = $(event.currentTarget).data('message-id');
                this.do_action({
                    type: 'ir.actions.act_window',
                    name: 'View Previous Editions',
                    res_model: 'wizard.view.previous.editions',
                    views: [[false, 'form']],
                    res_id: false,
                    target: 'new',
                    context: {'mail_message_id': message_id}
                });
            },
            "click .o_thread_message_edit": function (event) {
                var message_id = $(event.currentTarget).data('message-id');
                this.do_action({
                    type: 'ir.actions.act_window',
                    name: 'Edit Message',
                    res_model: 'wizard.edit.message',
                    views: [[false, 'form']],
                    res_id: false,
                    target: 'new',
                    context: {'mail_message_id': message_id}
                });
            },
        }),
    });
});
