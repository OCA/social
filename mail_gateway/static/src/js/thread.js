odoo.define("mail_broker.BrokerThread", function(require) {
    "use strict";
    var Thread = require("mail.model.Thread");

    var session = require("web.session");
    var field_utils = require("web.field_utils");

    var BrokerThread = Thread.extend({
        init: function(params) {
            this._messageIDs = [];
            var data = params.data;
            data.type = "broker_thread";
            this.resId = data.res_id;
            this._super.apply(this, arguments);
            this._messages = [];
            this.last_message_date = field_utils.parse.datetime(data.last_message_date);
            this.allHistoryLoaded = false;
            this.broker_id = data.broker_id;
            this._unreadCounter = data.unread;
        },
        getMessages: function() {
            return this._messages;
        },
        getLastSeenMessageID: function() {
            return null;
        },
        getNeedactionCounter: function() {
            return this._unreadCounter;
        },
        isGroupBasedSubscription: function() {
            return true;
        },
        _addMessage: function(message) {
            this._super.apply(this, arguments);
            if (_.contains(this._messages, message)) {
                return;
            }
            // Update internal list of messages
            this._messages.push(message);
            this._messages = _.sortBy(this._messages, function(msg) {
                return msg.getID();
            });
            // Update message ids associated to this document thread
            if (!_.contains(this._messageIDs, message.getID())) {
                this._messageIDs.push(message.getID());
            }
            if (message._date > this.last_message_date) {
                this.last_message_date = message._date;
            }
            if (message.isNeedaction()) {
                this._unreadCounter++;
            }
        },
        isAllHistoryLoaded: function() {
            return this.allHistoryLoaded;
        },
        fetchMessages: function(options) {
            return this._fetchMessages(options);
        },
        _fetchMessages: function(options) {
            var self = this;
            var domain = [];
            if (options && options.loadMore) {
                var minMessageID = this._messages[0].getID();
                domain = [["id", "<", minMessageID]].concat(domain);
            }
            return this._rpc({
                model: "mail.broker.channel",
                method: "message_fetch",
                args: [[this.resId], domain],
                kwargs: this._getFetchMessagesKwargs(options),
            }).then(function(messages) {
                if (!self.allHistoryLoaded) {
                    self.allHistoryLoaded = messages.length < self._FETCH_LIMIT;
                }
                _.each(messages, function(messageData) {
                    self.call("mail_service", "addMessage", messageData, {
                        silent: true,
                    });
                });
            });
        },
        _getFetchMessagesKwargs: function() {
            return {
                limit: this._FETCH_LIMIT,
                context: session.user_context,
            };
        },
        _postMessage: function(data) {
            var self = this;
            return this._super.apply(this, arguments).then(function(messageData) {
                _.extend(messageData, {
                    broker_type: "comment",
                    subtype: "mail.mt_comment",
                    command: data.command,
                });
                return self
                    ._rpc({
                        model: "mail.broker.channel",
                        method: "broker_message_post",
                        args: [[self.resId]],
                        kwargs: messageData,
                    })
                    .then(function() {
                        return messageData;
                    });
            });
        },
        _markAsRead: function() {
            var self = this;
            return this._super.apply(this, arguments).then(function() {
                self.call("mail_service", "markMessagesAsRead", self._messageIDs);
            });
        },
    });

    return BrokerThread;
});
