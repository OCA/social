/* Copyright 2019 Alexandre Díaz
   License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html). */
odoo.define('mail_tracking.FailedMessage', function (require) {
    "use strict";

    var AbstractField = require('web.AbstractField');
    var BasicModel = require('web.BasicModel');
    var BasicView = require('web.BasicView');
    var Chatter = require('mail.Chatter');
    var MailThread = require('mail.widget.Thread');
    var utils = require('mail.utils');
    var core = require('web.core');
    var field_registry = require('web.field_registry');
    var time = require('web.time');

    var QWeb = core.qweb;


    /**
    * Helper method to fetch failed messages
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
        *  Fetches the failed messages displayed by the 'mail_failed_message'
        * field widget in form views.
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
        * Mark failed message as reviewed. By default should be don't reviewed.
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

        /**
         * Overrides to listen bus notifications
         *
         * @Override
         */
        init: function () {
            this._super.apply(this, arguments);
            this.failed_messages = this.record.specialData[this.name];
            this.call(
                'bus_service', 'onNotification', this, this._onNotification);
        },

        /**
        * Paremeters used to render widget
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
        * Reset widget data using selected record
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
        * Trigger event to reload mail widgets
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
        * Listen bus notification to launch reload process.
        * This bus notification is received when the user uses
        * 'mail.resend.message' wizard.
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
                        // Reload 'mail_failed_message' widget
                        self._reload({failed_message: true});
                    }
                }
            });
        },

        /**
         * Handle retry failed message event to open the mail.resend.message
         * wizard.
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

        /**
        *  Overrides to add 'mail_failed_message' widget as "mail widget" used
        * in Chatter.
        *
        * @Override
        */
        init: function () {
            this._super.apply(this, arguments);
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
         *  Overrides to initialize 'mail_failed_message' widget.
         *
         * @Override
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
         * Injects widget before the chatter
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
         * Overrides to reload 'mail_failed_message' widget
         *
         * @Override
         */
        _onReloadMailFields: function (event) {
            if (this.fields.failed_message && event.data.failed_message) {
                this.trigger_up('reload', {
                    fieldNames: [this.fields.failed_message.name],
                    keepChanges: true,
                });
            } else {
                //  Workarround to avoid trigger reload event two times (one for
                // mail_failed_message and other with empty 'fieldNames'.
                this._super.apply(this, arguments);
            }
        },
    });

    MailThread.include({

        /**
         * Overrides to show 'retry' & 'Set as reviewed' buttons in the Chatter
         *
         * @Override
         */
        init: function () {
            this._super.apply(this, arguments);
            this._enabledOptions.displayRetryButton = true;
            this._enabledOptions.displayReviewedButton = true;
            this._disabledOptions.displayRetryButton = true;
            this._disabledOptions.displayReviewedButton = true;
        },
    });

    return FailedMessage;

});
