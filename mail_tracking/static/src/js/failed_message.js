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

        /**
         * Abstract method to be implemented
         *
         * @returns {Boolean}
         */
        isFailed: function () {
            return false;
        },
    });

    Message.include({

        /**
         * Init
         *
         * @param {Widget} parent
         * @param {Object} data
         */
        init: function (parent, data) {
            this._isFailedMessage = data.is_failed_message;
            this._super.apply(this, arguments);
        },

        /**
        * Implementation of the abstract method
        *
        * @returns {Boolean}
        */
        isFailed: function () {
            return _.contains(this._threadIDs, 'mailbox_failed');
        },

        /**
        * Adds/Remove message to/from failed thread
        *
        * @param {Boolean} failed
        */
        setFailed: function (failed) {
            if (failed) {
                this._addThread('mailbox_failed');
            } else {
                this.removeThread('mailbox_failed');
            }
        },

        /**
        * Process message mailbox
        */
        _processMailboxes: function () {
            this.setFailed(this._isFailedMessage);
            this._super.apply(this, arguments);
        },
    });

    MailManagerNotif.include({

        /**
         * Handle partner notification
         *
         * @private
         * @param {Object} data
         */
        _handlePartnerNotification: function (data) {
            if (data.type === 'toggle_tracking_status') {
                this._handlePartnerToggleFailedNotification(data);
            } else {
                this._super.apply(this, arguments);
            }
        },

        /**
        * Handle partner toggle failed notification
        *
        * @private
        * @param {Object} data
        */
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

        /**
        * Sidebar QWeb button params
        *
        * @private
        * @returns {Object}
        */
        _sidebarQWebParams: function () {
            var failed = this.call('mail_service', 'getMailbox', 'failed');
            return {
                activeThreadID: this._thread ? this._thread.getID() : undefined,
                failedCounter: failed.getMailboxCounter(),
            };
        },

        /**
        * Render sidebar failed button
        *
        * @private
        * @returns {jQueryElementt}
        */
        _renderSidebar: function () {
            var $sidebar = this._super.apply(this, arguments);
            // Because Odoo implementation isn't designed to be inherited
            // properly we inject failed button using jQuery.
            var $failed_item = $(QWeb.render('mail_tracking.SidebarFailed',
                this._sidebarQWebParams()));
            $failed_item.insertAfter(
                $sidebar.find(".o_mail_discuss_title_main").filter(":last"));
            return $sidebar;
        },

        /**
         * Message Updated
         *
         * @private
         * @param {Object} message
         * @param {String} type
         */
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
                // Workaround to avoid calling '_fetchAndRenderThread' when
                // it's not really needed.
                this._super.apply(this, arguments);
            }
        },

        /**
        * Get thread rendering options
        *
        * @private
        * @returns {Object}
        */
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

        /**
        * Start listening events
        *
        * @private
        */
        _startListening: function () {
            this._super.apply(this, arguments);
            this.call('mail_service', 'getMailBus')
                .on('update_failed', this, this._throttledUpdateThreads);
        },

        // Handlers
        /**
         * @private
         * @param {Event} event
         */
        _onRetryFailedMessage: function (event) {
            event.preventDefault();
            var messageID = $(event.currentTarget).data('message-id');
            this.do_action('mail.mail_resend_message_action', {
                additional_context: {
                    mail_message_to_resend: messageID,
                },
            });
        },

        /**
        * @private
        * @param {Event} event
        * @returns {Promise}
        */
        _onMarkFailedMessageReviewed: function (event) {
            event.preventDefault();
            var messageID = $(event.currentTarget).data('message-id');
            return this._rpc({
                model: 'mail.message',
                method: 'toggle_tracking_status',
                args: [[messageID]],
                context: this.getSession().user_context,
            });
        },
    });

    MailManager.include({

        /**
         * Create mailbox entry
         *
         * @private
         * @param {Object} data
         */
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

        /**
         * Get thread domain
         *
         * @private
         * @returns {Array}
         */
        _getThreadDomain: function () {
            if (this._id === 'mailbox_failed') {
                // Workaround to avoid throw an exception
                return [
                    ['mail_tracking_ids.state', 'in', FAILED_STATES],
                    ['mail_tracking_needs_action', '=', true],
                ];
            }
            return this._super.apply(this, arguments);
        },
    });


    /* FAILED MESSAGES CHATTER WIDGET */
    /**
    * Get messages with selected ids
    *
    * @private
    * @param {Object} self
    * @param {Array} ids
    * @returns {Array}
    */
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
            return messages;
        });
    }

    BasicModel.include({

        /**
        * Fetch special failed messages
        *
        * @private
        * @param {Object} record
        * @param {String} fieldName
        * @returns {Array}
        */
        _fetchSpecialFailedMessages: function (record, fieldName) {
            var localID = record._changes && fieldName in record._changes
                ? record._changes[fieldName] : record.data[fieldName];
            return _readMessages(this, this.localData[localID].res_ids);
        },
    });

    var AbstractFailedMessagesField = AbstractField.extend({

        /**
        * Abstract method to be implemented
        *
        * @returns {Boolean}
        */
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

        /**
        * Get message qweb parameters
        *
        * @private
        * @returns {Object}
        */
        _failedItemsQWebParams: function () {
            return {
                failed_messages: this.failed_messages,
                nbFailedMessages: this.failed_messages.length,
                date_format: time.getLangDateFormat(),
                datetime_format: time.getLangDatetimeFormat(),
            };
        },

        /**
        * Render failed message
        *
        * @private
        */
        _render: function () {
            if (this.failed_messages.length) {
                this.$el.html(QWeb.render(
                    'mail_tracking.failed_message_items',
                    this._failedItemsQWebParams()));
            } else {
                this.$el.empty();
            }
        },

        /**
        * Reset
        *
        * @private
        * @param {Object} record
        */
        _reset: function (record) {
            this._super.apply(this, arguments);
            this.failed_messages = this.record.specialData[this.name];
            this.res_id = record.res_id;
        },

        /**
        * Reload
        *
        * @private
        * @param {Array} fieldsToReload
        */
        _reload: function (fieldsToReload) {
            this.trigger_up('reload_mail_fields', fieldsToReload);
        },

        /**
        * Mark failed message as reviewed
        *
        * @private
        * @param {Int} id
        * @returns {Promise}
        */
        _markFailedMessageReviewed: function (id) {
            return this._rpc({
                model: 'mail.message',
                method: 'toggle_tracking_status',
                args: [[id]],
                context: this.record.getContext(),
            });
        },

        // Handlers
        /**
        * Listen notification to launch reload process
        *
        * @private
        * @param {Array} notifs
        */
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

        /**
         * Handle retry failed message event
         *
         * @private
         * @param {Event} event
         */
        _onRetryFailedMessage: function (event) {
            event.preventDefault();
            var messageID = $(event.currentTarget).data('message-id');
            this.do_action('mail.mail_resend_message_action', {
                additional_context: {
                    mail_message_to_resend: messageID,
                },
            });
        },

        /**
         * Handle mark message as reviewed event
         *
         * @private
         * @param {Event} event
         */
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

        /**
         * Init
         *
         * @private
         * @param {Widget} parent
         * @param {Object} record
         * @param {Object} mailFields
         * @param {Object} options
         */
        init: function (parent, record, mailFields, options) {
            this._super.apply(this, arguments);
            // Initialize mail_failed_message widget
            if (mailFields.mail_failed_message) {
                this.fields.failed_message = new FailedMessage(
                    this, mailFields.mail_failed_message, record, options);
            }
        },

        /**
         * Render
         *
         * @private
         * @returns {Promise}
         */
        _render: function () {
            var self = this;
            return this._super.apply(this, arguments).then(function () {
                if (self.fields.failed_message) {
                    self.fields.failed_message.$el.insertBefore(
                        self.$el.find('.o_mail_thread'));
                }
            });
        },

        /**
         * Handle reload fields event
         *
         * @private
         * @param {Event} event
         */
        _onReloadMailFields: function (event) {
            if (this.fields.failed_message && event.data.failed_message) {
                this.trigger_up('reload', {
                    fieldNames: [this.fields.failed_message.name],
                    keepChanges: true,
                });
            } else {
                // Workarround to avoid trigger reload event two times.
                this._super.apply(this, arguments);
            }
        },
    });

    return FailedMessage;

});
