/* © 2014-2015 Grupo ESOC <www.grupoesoc.es>
 * License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
 */

odoo.define('mail_forward.forward', function (require) {
    "use strict";
    var core = require('web.core');
    var ChatThread = require('mail.ChatThread');
    var chat_manager = require('mail.chat_manager');
    var Model = require('web.Model');
    var session = require('web.session');
    var MessageModel = new Model('mail.message', session.user_context);
    var _t = core._t;

    ChatThread.include({
        on_message_forward: function (message_id) {
            var self = this;
            var read_fields = ['record_name', 'parent_id', 'subject', 'attachment_ids', 'date',
                'email_to', 'email_from', 'email_cc', 'model', 'res_id', 'body'];
            // Generate email subject as possible from record_name and subject
            MessageModel.call('read', [message_id, read_fields], {context: session.user_context}).then(function (result) {
                var message = result[0];
                var subject = [_t("FWD")];
                if (message.record_name && message.parent_id) {
                    subject.push(message.record_name);
                }
                if (message.subject) {
                    subject.push(message.subject);
                } else if (subject.length < 2) {
                    subject.push(_t("(No subject)"));
                }

                // Get only ID from the attachments
                var attachment_ids = [];
                for (var n in message.attachment_ids) {
                    attachment_ids.push(message.attachment_ids[n]);
                }

                // Get necessary fields from the forwarded message
                var header = [
                    "----------" + _t("Forwarded message") + "----------",
                    _t("From: ") + message.email_from,
                    _t("Date: ") + message.date
                ];
                if (message.subject) {
                    header.push(_t("Subject: ") + message.subject);
                }
                if (message.email_to) {
                    header.push(_t("To: ") + message.email_to);
                }
                if (message.email_cc) {
                    header.push(_t("CC: ") + message.email_cc);
                }
                header = header.map(_.str.escapeHTML).join("<br/>");

                var context = {
                    default_attachment_ids: attachment_ids,
                    default_body:
                    "<p><i>" + header + "</i></p><br/>" +
                    message.body,
                    default_model: message.model,
                    default_res_id: message.res_id,
                    default_subject: subject.join(": ")
                };

                if (message.model && message.res_id) {
                    context.default_destination_object_id =
                        [message.model, message.res_id].join();
                }

                // Get the action data and execute it to open the composer wizard
                var do_action = self.do_action;
                self.rpc("/web/action/load", {
                    "action_id": "mail_forward.compose_action"
                })
                    .done(function (action) {
                        action.context = context;
                        do_action(action, {
                            on_close: $.proxy(self.thread_reload, self)
                        });
                    });
            });
        },
        init: function (parent, options) {
            this._super.apply(this, arguments);
            // Add click reaction in the events of the thread object
            this.events['click .o_forward'] = function (event) {
                var message_id = $(event.currentTarget).data('message-id');
                this.trigger("message_forward", message_id);
            };
        },
        thread_reload: function(){
            var parent = this.getParent();
            var domain = [['model', '=', parent.model], ['res_id', '=', parent.res_id]];
            var self = this;
            MessageModel.call('message_fetch', [domain], {limit: 30}).then(function (msgs) {
                var messages = _.map(msgs, chat_manager.make_message);
                // Avoid displaying in reverse order
                self.options.display_order = 1;
                self.render(messages, self.options)
            });
        }
    });

    var chatter = require('mail.Chatter');
    chatter.include({
        start: function () {
            var result = this._super.apply(this, arguments);
            this.thread.on('message_forward', this, this.thread.on_message_forward);
            return result;
        }
    });

    var ChatAction = core.action_registry.get('mail.chat.instant_messaging');
    ChatAction.include({
        start: function () {
            var result = this._super.apply(this, arguments);
            // For show wizard in the channels
            this.thread.on('message_forward', this, this.thread.on_message_forward);
            return result;
        }
    });
});
