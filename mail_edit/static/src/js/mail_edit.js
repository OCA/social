/* © 2014-2017 Sunflower IT <www.sunflowerweb.nl>*/

 odoo.define('mail_edit.mail_edit', function (require) {
"use strict";

    var Message = require('mail.model.Message');
    var Dialog = require('web.Dialog');
    var ThreadWidget = require('mail.widget.Thread');
    var session = require('web.session');
    var SearchableThread = require('mail.model.SearchableThread');
    var DocumentThread = require('mail.model.DocumentThread');

    var core = require('web.core');
    var _t = core._t;

    SearchableThread.include({
        init: function() {
            this._super.apply(this, arguments);
            this.isSearchableThread = true;
        }
    });

    DocumentThread.include({
        init: function() {
            this._super.apply(this, arguments);
            this.isDocumentThread = true;
        },

        mailEditRemoveMessage: function(messageID) {
            this._messages = _.reject(this._messages, function (message) {
                return message.getID() === messageID;
            });
        }
    });

    ThreadWidget.include({

        events: _.defaults({
            "click .o_mail_edit": "_onClickMessageEdit",
            "click .o_mail_delete": "_onClickMessageDelete",
        }, ThreadWidget.prototype.events),

        _onClickMessageEdit: function(event) {
            var self = this;
            var do_action = self.do_action,
                msg_id = $(event.currentTarget).data('message-id');

            self._rpc({
                route: "/web/action/load",
                params: {
                    action_id: "mail_edit.mail_edit_action",
                },
            })
            .done(function (action) {
                action.res_id = msg_id;
                return self.do_action(action, {
                    on_close: function () {
                        var message = self.call('mail_service', 'getMessage', msg_id);
                        self._rpc({
                            model: 'mail.message',
                            method: 'message_format',
                            args: [msg_id],
                            context: session.user_context,
                        })
                        .then(function (messagesData) {
                            var thread = self.call('mail_service', 'getThread', self._currentThreadID);
                            // TODO: update other fields as well, and call processBody.
                            message._body = messagesData[0].body;
                            self.render(thread, {});
                        });
                    },
                });
            });
        },

        _onClickMessageDelete: function(event, options) {
            var self = this;
            event.stopPropagation();
            event.preventDefault();
            var msg_id = $(event.currentTarget).data('message-id');
            Dialog.confirm(
                self,
                _t("Do you really want to delete this message?"), {
                    confirm_callback: function () {
                        return self._rpc({
                            model: 'mail.message',
                            method: 'unlink',
                            args: [[msg_id]],
                        })
                        .then(function() {
                            var thread = self.call('mail_service', 'getThread', self._currentThreadID);
                            if (thread.isSearchableThread) {
                                thread.removeMessage(msg_id);
                                self.removeMessageAndRender(msg_id, thread, {});
                            } else if (thread.isDocumentThread) {
                                thread.mailEditRemoveMessage(msg_id);
                                self.removeMessageAndRender(msg_id, thread, {});
                            }
                        });
                    },
                }
            );

        }

    });

    Message.include({
        init: function (parent, data) {
            this._super.apply(this, arguments);
            this.is_superuser = data.is_superuser || false;
            this.is_author = data.is_author || false;
        },
    });

});
