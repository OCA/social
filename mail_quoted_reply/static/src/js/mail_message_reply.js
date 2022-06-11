/* Copyright 2021 Creu Blanca
 * License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
 */
odoo.define("mail_quote_reply.reply", function(require) {
    "use strict";

    var ThreadWidget = require("mail.widget.Thread");
    var ThreadField = require("mail.ThreadField");
    var DocumentThread = require("mail.model.DocumentThread");

    DocumentThread.include({
        _fetchMessages: function(options) {
            if (options && options.forceReloadMessages) {
                this._mustFetchMessageIDs = true;
            }
            return this._super.apply(this, arguments);
        },
    });

    ThreadField.include({
        start: function() {
            var self = this;
            return this._super.apply(this, arguments).then(function() {
                self._threadWidget.on(
                    "reload_thread_messages",
                    self,
                    self._onReloadThreadMessages
                );
            });
        },
        _onReloadThreadMessages: function() {
            this._fetchAndRenderThread({forceReloadMessages: true});
        },
    });

    ThreadWidget.include({
        events: _.defaults(
            {
                "click .o_thread_mail_message_reply": "_onClickMailMessageReply",
            },
            ThreadWidget.prototype.events
        ),

        _onClickMailMessageReply: function(event) {
            var self = this,
                msg_id = $(event.currentTarget).data("message-id");
            this._rpc({
                model: "mail.message",
                method: "reply_message",
                args: [msg_id],
            }).then(function(result) {
                self.do_action(result, {
                    on_close: function() {
                        self.trigger("reload_thread_messages");
                    },
                });
            });
        },
    });
});
