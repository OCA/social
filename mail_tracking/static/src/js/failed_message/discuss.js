/* Copyright 2019 Alexandre Díaz
   License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html). */
odoo.define('mail_tracking.FailedMessageDiscuss', function (require) {
    "use strict";

    // To be considered:
    //   - One message can be displayed in many threads
    //   - A thread can be a mailbox, channel, ...
    //   - A mailbox is a type of thread that is displayed on top of
    //    the discuss menu, has a counter, etc...

    var MailManagerNotif = require('mail.Manager.Notification');
    var AbstractMessage = require('mail.model.AbstractMessage');
    var Message = require('mail.model.Message');
    var Discuss = require('mail.Discuss');
    var MailManager = require('mail.Manager');
    var Mailbox = require('mail.model.Mailbox');
    var Dialog = require('web.Dialog');
    var core = require('web.core');

    var QWeb = core.qweb;
    var _t = core._t;


    AbstractMessage.include({

        /**
         * Abstract declaration to know if a message is included in the
         * failed mailbox. By default it should be false.
         *
         * @returns {Boolean}
         */
        isFailed: function () {
            return false;
        },
    });

    Message.include({

        /**
         * Overrides to store information from server
         *
         * @override
         */
        init: function (parent, data) {
            this._isFailedMessage = data.is_failed_message;
            return this._super.apply(this, arguments);
        },

        /**
         * Implementation to know if a message is included in the
         * failed mailbox.
         *
         * @override
         */
        isFailed: function () {
            return _.contains(this._threadIDs, 'mailbox_failed');
        },

        /**
         * Adds/Removes message to/from failed mailbox
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
         * Include the message in the 'failed' mailbox if needed
         *
         * @override
         */
        _processMailboxes: function () {
            this.setFailed(this._isFailedMessage);
            return this._super.apply(this, arguments);
        },
    });

    MailManagerNotif.include({

        /**
         * Overrides to handle changes in the 'mail_tracking_needs_action' flag
         *
         * @override
         */
        _handlePartnerNotification: function (data) {
            if (data.type === 'toggle_tracking_status') {
                this._handleChangeTrackingNeedsActionNotification(data);
            } else {
                // Workaround to avoid call '_handlePartnerChannelNotification'
                // because this is related with the failed mailbox, not a
                // channel.
                this._super.apply(this, arguments);
            }
        },

        /**
         * This method updates messages in the failed mailbox when the flag
         * 'mail_tracking_needs_action' was changed to False. This can
         * remove/add the message from/to failed mailbox and update mailbox
         * counter.
         *
         * @private
         * @param {Object} data
         */
        _handleChangeTrackingNeedsActionNotification: function (data) {
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
                    self._mailBus.trigger('update_message', message, data.type);
                }
            });

            if (data.needs_actions) {
                // Increase failed counter if message is marked as failed
                failed.incrementMailboxCounter(data.message_ids.length);
            } else {
                // Decrease failed counter if message is removed from failed
                failed.decrementMailboxCounter(data.message_ids.length);
            }

            // Trigger event to refresh threads
            this._mailBus.trigger('update_failed', failed.getMailboxCounter());
        },
    });

    Discuss.include({
        events: _.extend({}, Discuss.prototype.events, {
            'click .o_failed_message_retry': '_onRetryFailedMessage',
            'click .o_failed_message_reviewed': '_onMarkFailedMessageReviewed',
        }),

        /**
         * Paramaters used to render 'failed' mailbox entry in Discuss
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
         * Render 'failed' mailbox menu entry in Discuss
         *
         * @private
         * @returns {jQueryElementt}
         */
        _renderSidebar: function () {
            var $sidebar = this._super.apply(this, arguments);
            // Because Odoo implementation isn't designed to be inherited
            // properly, we inject 'failed' button using jQuery.
            var $failed_item = $(QWeb.render('mail_tracking.SidebarFailed',
                this._sidebarQWebParams()));
            $failed_item.insertAfter(
                $sidebar.find(".o_mail_discuss_title_main").filter(":last"));
            return $sidebar;
        },

        /**
         * Overrides to listen click on 'Set all as reviewed' button
         *
         * @override
         */
        _renderButtons: function () {
            this._super.apply(this, arguments);
            this.$btn_set_all_reviewed = this.$buttons.find(
                '.o_mail_discuss_button_set_all_reviewed');
            this.$btn_set_all_reviewed
                .on('click', $.proxy(this, "_onSetAllAsReviewedClicked"));
        },

        /**
         * Show or hide 'set all as reviewed' button in discuss mailbox
         *
         * This means in which thread the button should be displayed.
         *
         * @override
         */
        _updateControlPanelButtons: function (thread) {
            this.$btn_set_all_reviewed
                .toggleClass(
                    'd-none',
                    thread.getID() !== 'mailbox_failed')
                .toggleClass(
                    'd-md-inline-block',
                    thread.getID() === 'mailbox_failed');

            return this._super.apply(this, arguments);
        },

        /**
         * Overrides to update 'set all as reviewed' button.
         *
         * Disabled button if doesn't have more failed messages
         *
         * @override
         */
        _updateButtonStatus: function (disabled, type) {
            if (this._thread.getID() === 'mailbox_failed') {
                this.$btn_set_all_reviewed
                    .toggleClass('disabled', disabled);
                // Display Rainbowman when all failed messages are reviewed
                // through 'TOGGLE TRACKING STATUS' or marking last failed
                // message as reviewed
                if (disabled && type === 'toggle_tracking_status') {
                    this.trigger_up('show_effect', {
                        message: _t(
                            "Congratulations, your failed mailbox is empty"),
                        type: 'rainbow_man',
                    });
                }
            }
        },

        /**
         * Overrides to update messages in 'failed' mailbox thread
         *
         * @override
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
                // Workaround to avoid calling '_fetchAndRenderThread' and
                // refetching thread messages because these messages are
                // actually fetched above.
                this._super.apply(this, arguments);
            }
        },

        /**
         * Hide reply feature in the 'failed' mailbox, where it has no sense.
         * Show instead 'Retry' and 'Set as reviewed' buttons.
         *
         * @override
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
         * Listen also to the event that refreshes thread messages
         *
         * @override
         */
        _startListening: function () {
            this._super.apply(this, arguments);
            this.call('mail_service', 'getMailBus')
                .on('update_failed', this, this._throttledUpdateThreads);
        },

        // Handlers
        /**
         * Open the resend mail.resend.message wizard
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
         * Toggle 'mail_tracking_needs_action' flag
         *
         * @private
         * @param {Event} event
         * @returns {Promise}
         */
        _onMarkFailedMessageReviewed: function (event) {
            event.preventDefault();
            var messageID = $(event.currentTarget).data('message-id');
            return this._rpc({
                model: 'mail.message',
                method: 'set_need_action_done',
                args: [[messageID]],
                context: this.getSession().user_context,
            });
        },

        /**
         * Inheritable method that call thread implementation
         *
         * @private
         */
        _onSetAllAsReviewedClicked: function () {
            var self = this;
            var failed = this.call('mail_service', 'getMailbox', 'failed');
            var promptText = _.str.sprintf(
                _t("Do you really want to mark as reviewed all the" +
                    " failed messages (%d)?"),
                failed.getMailboxCounter());
            Dialog.confirm(this, promptText, {
                confirm_callback: function () {
                    self._thread.setAllMessagesAsReviewed();
                },
            });
        },
    });

    MailManager.include({

        /**
         * Add the 'failed' mailbox
         *
         * @override
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
         * Overrides to add domain for 'failed' mailbox thread
         *
         * @override
         */
        _getThreadDomain: function () {
            if (this._id === 'mailbox_failed') {
                return [['is_failed_message', '=', true]];
            }
            // Workaround to avoid throw 'Missing domain' exception. Call _super
            // without a valid (hard-coded) thread id causes that exeception.
            return this._super.apply(this, arguments);
        },

        /**
         * Sets all messages from the mailbox as reviewed.
         *
         * At the moment, this method makes only sense for 'Failed'.
         *
         * @returns {$.Promise} resolved when all messages have been marked as
         *   reviewed on the server
         */
        setAllMessagesAsReviewed: function () {
            if (this._id === 'mailbox_failed' && this.getMailboxCounter() > 0) {
                return this._rpc({
                    model: 'mail.message',
                    method: 'set_all_as_reviewed',
                });
            }
            return $.when();
        },
    });

});
