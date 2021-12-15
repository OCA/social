odoo.define("mail_broker.mail.Manager", function(require) {
    "use strict";
    var Manager = require("mail.Manager");
    var BrokerThread = require("mail_broker.BrokerThread");

    Manager.include({
        _addMessageToThreads: function(message, options) {
            this._super.apply(this, arguments);
            if (message.broker_channel_id) {
                var thread = this.getThread(
                    "broker_thread_" + message.broker_channel_id
                );
                if (thread) {
                    thread.addMessage(message, options);
                }
            }
        },
        _updateInternalStateFromServer: function(result) {
            this._super.apply(this, arguments);
            this._updateBrokerChannelFromServer(result);
        },
        getBrokerBots: function() {
            var data = _.extend({}, this._broker_bots);
            _.each(data, function(value) {
                value.threads = [];
            });
            _.each(this._threads, function(thread) {
                if (thread.getType() === "broker_thread") {
                    data[thread.broker_id].threads.push(thread);
                }
            });
            _.each(data, function(value) {
                value.threads.sort(function(a, b) {
                    return b.last_message_date - a.last_message_date;
                });
            });
            return data;
        },
        _updateBrokerChannelFromServer: function(data) {
            var self = this;
            this._broker_bots = {};
            _.each(data.broker_slots, function(slot) {
                self._broker_bots[slot.id] = {
                    name: slot.name,
                    channel_name: slot.channel_name,
                };
                _.each(slot.threads, self._addChannel.bind(self));
            });
        },
        getMailBrokerThreads: function() {
            var data = _.filter(this._threads, function(thread) {
                return thread.getType() === "broker_thread";
            });
            data = data.sort(function(a, b) {
                return b.last_message_date - a.last_message_date;
            });
            return data;
        },
        _makeChannel: function(data, options) {
            if (data.channel_type === "broker_thread") {
                return new BrokerThread({
                    parent: this,
                    data: data,
                    options: options,
                    commands: this._commands,
                });
            }
            return this._super.apply(this, arguments);
        },
        _onNotification: function(notifs) {
            var self = this;
            var result = this._super.apply(this, arguments);
            _.each(notifs, function(notif) {
                if (notif[0][1] === "mail.broker") {
                    if (notif[1].message) {
                        self.addMessage(notif[1].message, {silent: 0});
                    } else if (notif[1].thread) {
                        self._addChannel(notif[1].thread);
                    }
                }
            });
            return result;
        },
    });
});
