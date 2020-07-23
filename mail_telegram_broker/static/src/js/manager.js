odoo.define('telegram.mail.Manager', function (require) {
    "use strict";
    var Manager = require('mail.Manager');
    var TelegramThread = require('telegram.TelegramThread');

    Manager.include({
        _addMessageToThreads: function (message, options) {
            this._super.apply(this, arguments);
            if (message.telegram_chat_id) {
                var thread = this.getThread(
                    'telegram_thread_' + message.telegram_chat_id);
                if (thread) {
                    thread.addMessage(message, options);
                }
            }
        },
        _updateInternalStateFromServer: function (result) {
            this._super.apply(this, arguments);
            this._updateTelegramChatFromServer(result);
        },
        getTelegramBots: function () {
            var data = _.extend({}, this._telegram_bots);
            _.each(data, function (value) {
                value.threads = [];
            });
            _.each(this._threads, function (thread) {
                if (thread.getType() === 'telegram_thread') {
                    data[thread.bot_id].threads.push(thread);
                }
            });
            _.each(data, function (value) {
                value.threads.sort(function (a, b) {
                    return b.last_message_date - a.last_message_date;
                });
            });
            return data;
        },
        _updateTelegramChatFromServer: function (data) {
            var self = this;
            this._telegram_bots = {};
            _.each(data.telegram_slots, function (slot) {
                self._telegram_bots[slot.id] = {
                    'name': slot.name,
                    'channel_name': slot.channel_name,
                };
                _.each(slot.threads, self._addChannel.bind(self));
            });
        },
        getTelegramThreads: function () {
            var data = _.filter(this._threads, function (thread) {
                return thread.getType() === 'telegram_thread';
            });
            data = data.sort(function (a, b) {
                return b.last_message_date - a.last_message_date;
            });
            return data;
        },
        _makeChannel: function (data, options) {
            if (data.channel_type === 'telegram_thread') {
                return new TelegramThread({
                    parent: this,
                    data: data,
                    options: options,
                    commands: this._commands,
                });
            }
            return this._super.apply(this, arguments);
        },
        _onNotification: function (notifs) {
            var self = this;
            var result = this._super.apply(this, arguments);
            _.each(notifs, function (notif) {
                if (notif[0][1] === 'mail.telegram.bot') {
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
