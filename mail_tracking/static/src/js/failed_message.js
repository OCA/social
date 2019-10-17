/* Copyright 2019 Alexandre Díaz
   License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html). */
odoo.define('mail_tracking.FailedMessage', function (require) {
    "use strict";

    var AbstractField = require('web.AbstractField');
    var BasicModel = require('web.BasicModel');
    var BasicView = require('web.BasicView');
    var Chatter = require('mail.Chatter');
    var Discuss = require('mail.Discuss');
    var MailManager = require('mail.Manager');
    var Mailbox = require('mail.model.Mailbox');
    var MailManagerNotif = require('mail.Manager.Notification');
    var AbstractMessage = require('mail.model.AbstractMessage');
    var Message = require('mail.model.Message');
    var utils = require('mail.utils');
    var core = require('web.core');
    var field_registry = require('web.field_registry');
    var time = require('web.time');

    var QWeb = core.qweb;
    var _t = core._t;

    var FAILED_STATES = [
        'error', 'rejected', 'spam', 'bounced', 'soft-bounced',
    ];


    /* COMMON */
    AbstractMessage.include({
        isFailed: function () {
            return false;
        },
    });

    Message.include({
        init: function (parent, data) {
            this._isFailedMessage = data.failed_message;
            this._super.apply(this, arguments);
        },

        isFailed: function () {
            return _.contains(this._threadIDs, 'mailbox_failed');
        },

        setFailed: function (failed) {
            if (failed) {
                this._addThread('mailbox_failed');
            } else {
                this.removeThread('mailbox_failed');
            }
        },

        _processMailboxes: function () {
            this.setFailed(this._isFailedMessage);
            this._super.apply(this, arguments);
        },
    });

    MailManagerNotif.include({
        _handlePartnerNotification: function (data) {
            if (data.type === 'toggle_tracking_status') {
                this._handlePartnerToggleFailedNotification(data);
            } else {
                this._super.apply(this, arguments);
            }
        },

        _handlePartnerToggleFailedNotification: function (data) {
            var self = this;
            var failed = this.getMailbox('failed');
            _.each(data.message_ids, function (messageID) {
                var message = _.find(self._messages, function (msg) {
                    return msg.getID() === messageID;
                });
                if (message) {
                    message.setFailed(data.needs_actions);
                    if (message.isFailed() === false) {
                        self._removeMessageFromThread(
                            'mailbox_failed', message);
                    } else {
                        self._addMessageToThreads(message, []);
                        var channelFailed = self.getMailbox('failed');
                        channelFailed.invalidateCaches();
                    }
                    self._mailBus.trigger('update_message', message);
                }
            });

            if (data.needs_actions) {
                // Increase failed counter if message is marked as failed
                failed.incrementMailboxCounter(data.message_ids.length);
            } else {
                // Decrease failed counter if message is remove from failed
                failed.decrementMailboxCounter(data.message_ids.length);
            }

            this._mailBus.trigger('update_failed', failed.getMailboxCounter());
        },
    });


    /* DISCUSS */
    Discuss.include({
        events: _.extend({}, Discuss.prototype.events, {
            'click .o_failed_message_retry': '_onRetryFailedMessage',
            'click .o_failed_message_reviewed': '_onMarkFailedMessageReviewed',
        }),

        _sidebarQWebParams: function () {
            var failed = this.call('mail_service', 'getMailbox', 'failed');
            return {
                activeThreadID: this._thread ? this._thread.getID() : undefined,
                failedCounter: failed.getMailboxCounter(),
            };
        },

        _renderSidebar: function () {
            var $sidebar = this._super.apply(this, arguments);
            // Because Odoo implementation isn't designed to be inherited
            // properly we inject failed button using jQuery.
            var $sidebarFailed = $(QWeb.render('mail_tracking.SidebarFailed',
                this._sidebarQWebParams()));
            $sidebarFailed.insertBefore($sidebar.find("hr[class='mb8']"));
            return $sidebar;
        },

        _onMessageUpdated: function (message, type) {
            var self = this;
            var currentThreadID = this._thread.getID();
            if (currentThreadID === 'mailbox_failed' && !message.isFailed()) {
                this._thread.fetchMessages(this.domain)
                    .then(function () {
                        var options = self._getThreadRenderingOptions();
                        self._threadWidget.removeMessageAndRender(
                            message.getID(), self._thread, options)
                            .then(function () {
                                self._updateButtonStatus(
                                    !self._thread.hasMessages(), type);
                            });
                    });
            } else {
                this._super.apply(this, arguments);
            }
        },

        _getThreadRenderingOptions: function () {
            var values = this._super.apply(this, arguments);
            if (this._thread.getID() === 'mailbox_failed') {
                values.displayEmailIcons = true;
                values.displayReplyIcons = false;
                values.displayRetryButton = true;
                values.displayReviewedButton = true;
            }
            return values;
        },

        _startListening: function () {
            this._super.apply(this, arguments);
            this.call('mail_service', 'getMailBus')
                .on('update_failed', this, this._throttledUpdateThreads);
        },

        // Handlers
        _onRetryFailedMessage: function (event) {
            event.preventDefault();
            var messageID = $(event.currentTarget).data('message-id');
            this.do_action('mail.mail_resend_message_action', {
                additional_context: {
                    mail_message_to_resend: messageID,
                },
            });
        },

        _onMarkFailedMessageReviewed: function (event) {
            event.preventDefault();
            var messageID = $(event.currentTarget).data('message-id');
            this._rpc({
                model: 'mail.message',
                method: 'toggle_tracking_status',
                args: [[messageID]],
                context: this.getSession().user_context,
            });
        },
    });

    MailManager.include({
        _updateMailboxesFromServer: function (data) {
            this._super.apply(this, arguments);
            this._addMailbox({
                id: 'failed',
                name: _t("Failed"),
                mailboxCounter: data.failed_counter || 0,
            });
        },
    });

    Mailbox.include({
        _getThreadDomain: function () {
            if (this._id === 'mailbox_failed') {
                return [
                    ['mail_tracking_ids.state', 'in', FAILED_STATES],
                    ['mail_tracking_needs_action', '=', true],
                ];
            }
            return this._super.apply(this, arguments);
        },
    });


    /* FAILED MESSAGES CHATTER WIDGET */
    function _readMessages (self, ids) {
        if (!ids.length) {
            return $.when([]);
        }
        var context = self.record && self.record.getContext();
        return self._rpc({
            model: 'mail.message',
            method: 'get_failed_messages',
            args: [ids],
            context: context || self.getSession().user_context,
        }).then(function (messages) {
            // Convert date to moment
            _.each(messages, function (msg) {
                msg.date = moment(time.auto_str_to_date(msg.date));
                msg.hour = utils.timeFromNow(msg.date);
            });
            return _.sortBy(messages, 'date');
        });
    }

    BasicModel.include({
        _fetchSpecialFailedMessages: function (record, fieldName) {
            var localID = record._changes && fieldName in record._changes
                ? record._changes[fieldName] : record.data[fieldName];
            return _readMessages(this, this.localData[localID].res_ids);
        },
    });

    var AbstractFailedMessagesField = AbstractField.extend({
        _markFailedMessageReviewed: function () {
            return false;
        },
    });

    var FailedMessage = AbstractFailedMessagesField.extend({
        className: 'o_mail_failed_message',
        events: {
            'click .o_failed_message_retry': '_onRetryFailedMessage',
            'click .o_failed_message_reviewed': '_onMarkFailedMessageReviewed',
        },
        specialData: '_fetchSpecialFailedMessages',

        init: function () {
            this._super.apply(this, arguments);
            this.failed_messages = this.record.specialData[this.name];
            this.call(
                'bus_service', 'onNotification', this, this._onNotification);
        },

        _onNotification: function (notifs) {
            var self = this;
            _.each(notifs, function (notif) {
                var model = notif[0][1];
                if (model === 'res.partner') {
                    var data = notif[1];
                    if (data.type === 'update_failed_messages') {
                        // Update failed messages
                        self._reload({failed_message: true});
                    }
                }
            });
        },

        _failedItemsQWebParams: function () {
            return {
                failed_messages: this.failed_messages,
                nbFailedMessages: this.failed_messages.length,
                date_format: time.getLangDateFormat(),
                datetime_format: time.getLangDatetimeFormat(),
            };
        },

        _render: function () {
            if (this.failed_messages.length) {
                this.$el.html(QWeb.render(
                    'mail_tracking.failed_message_items',
                    this._failedItemsQWebParams()));
            } else {
                this.$el.empty();
            }
        },
        _reset: function (record) {
            this._super.apply(this, arguments);
            this.failed_messages = this.record.specialData[this.name];
            this.res_id = record.res_id;
        },

        _reload: function (fieldsToReload) {
            this.trigger_up('reload_mail_fields', fieldsToReload);
        },

        _markFailedMessageReviewed: function (id) {
            return this._rpc({
                model: 'mail.message',
                method: 'toggle_tracking_status',
                args: [[id]],
                context: this.record.getContext(),
            });
        },

        // Handlers
        _onRetryFailedMessage: function (event) {
            event.preventDefault();
            var messageID = $(event.currentTarget).data('message-id');
            this.do_action('mail.mail_resend_message_action', {
                additional_context: {
                    mail_message_to_resend: messageID,
                },
            });
        },

        _onMarkFailedMessageReviewed: function (event) {
            event.preventDefault();
            var messageID = $(event.currentTarget).data('message-id');
            this._markFailedMessageReviewed(messageID).then(
                this._reload.bind(this, {failed_message: true}));
        },
    });

    field_registry.add('mail_failed_message', FailedMessage);

    var mailWidgets = ['mail_failed_message'];
    BasicView.include({
        init: function () {
            this._super.apply(this, arguments);
            // Adds mail_failed_message as valid mail widget
            var fieldsInfo = this.fieldsInfo[this.viewType];
            for (var fieldName in fieldsInfo) {
                var fieldInfo = fieldsInfo[fieldName];
                if (_.contains(mailWidgets, fieldInfo.widget)) {
                    this.mailFields[fieldInfo.widget] = fieldName;
                    fieldInfo.__no_fetch = true;
                }
            }
            Object.assign(this.rendererParams.mailFields, this.mailFields);
        },
    });

    Chatter.include({
        init: function (parent, record, mailFields, options) {
            this._super.apply(this, arguments);
            // Initialize mail_failed_message widget
            if (mailFields.mail_failed_message) {
                this.fields.failed_message = new FailedMessage(
                    this, mailFields.mail_failed_message, record, options);
            }
        },

        _render: function () {
            var self = this;
            return this._super.apply(this, arguments).then(function () {
                if (self.fields.failed_message) {
                    self.fields.failed_message.$el.insertBefore(
                        self.$el.find('.o_mail_thread'));
                }
            });
        },

        _onReloadMailFields: function (event) {
            if (this.fields.failed_message && event.data.failed_message) {
                this.trigger_up('reload', {
                    fieldNames: [this.fields.failed_message.name],
                    keepChanges: true,
                });
            } else {
                this._super.apply(this, arguments);
            }
        },
    });

    return FailedMessage;

});
