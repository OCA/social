odoo.define('mail_notify.Manager', function (require) {
"use strict";
var config = require('web.config');
var core = require('web.core');
var mailUtils = require('mail.utils');
var _t = core._t;
var MailManagerNotification = require('mail.Manager.Notification');
var MailManager = require('mail.Manager');

var PREVIEW_MSG_MAX_SIZE = 350;
var rpc = require('web.rpc');

MailManagerNotification.include({
    _addNewMessagePostprocessThread: function (message, options) {
        var self = this;
        _.each(message.getThreadIDs(), function (threadID) {
            var thread = self.getThread(threadID);
            if (thread) {
                if (
                    thread.getType() !== 'mailbox' &&
                    !message.isMyselfAuthor() &&
                    !message.isSystemNotification()
                ) {
                    if (thread.isTwoUserThread() && options.showNotification) {
                        if (
                            !self._isDiscussOpen() &&
                            !config.device.isMobile &&
                            !thread.isDetached()
                        ) {
                            // automatically open thread window
                            // while keeping it unread
                            thread.detach({ passively: true });
                        }
                        var query = { isVisible: false };
                        self._mailBus.trigger('is_thread_bottom_visible', thread, query);
                    }
                    if (options.showNotification) {
                        if (!self.call('bus_service', 'isOdooFocused')) {
                            var ir_config = rpc.query({
                                model: 'ir.config_parameter',
                                method: 'get_fcm_config',
                            }).then(function(result){
                                if (!result.is_fcm_enabled) {
                                    self._notifyIncomingMessage(message);
                                }
                            });
                        }
                    }
                }
            }
        });
    },

    _notifyIncomingMessage: function (message) {
        if (this.call('bus_service', 'isOdooFocused')) {
            // no need to notify
            return;
        }
        var icon = false;

        //Set icon to module icon by defaut
        if (Boolean(message._getModuleIcon())) {
            icon = message._getModuleIcon();
        }
        // for instant messaging the icon will be set to the user avatar
        if (message.getDocumentModel() == "mail.channel" && Boolean(message.getAvatarSource())) {
            icon = message.getAvatarSource();
        }
        var title = _t("New message");
        if (message.hasAuthor()) {
            title = _.escape(message.getAuthorName());
        }

        if (message.hasSubject()) {
            title = title + ": " + message.getSubject();
        }
        else if (message.getDocumentModel() != "mail.channel" && message.getDocumentName()) {
            title = title + ": " + message.getDocumentName();
        }
        var content = mailUtils.parseAndTransform(message.getBody(), mailUtils.stripHTML).substr(0, PREVIEW_MSG_MAX_SIZE);

        if (!this.call('bus_service', 'isOdooFocused')) {
            this._outOfFocusUnreadMessageCounter++;
            var tabTitle = _.str.sprintf(
                _t("%d Messages"),
                this._outOfFocusUnreadMessageCounter
            );
            this.trigger_up('set_title_part', {
                part: '_chat',
                title: tabTitle
            });
        }
        this.call('bus_service', 'sendNotification', title, content, function ( ){window.open(message.getURL());}, icon);
    },

    _handleNeedactionNotification: function (messageData) {
        var self = this;
        var inbox = this.getMailbox('inbox');
        var message = this.addMessage(messageData, {
            incrementUnread: true,
            showNotification: true,
        });
        if (typeof inbox != "undefined") {
            inbox.incrementMailboxCounter();
        }
        _.each(message.getThreadIDs(), function (threadID) {
            var channel = self.getChannel(threadID);
            if (channel) {
                channel.incrementNeedactionCounter();
            }
        });
        this._mailBus.trigger('update_needaction', inbox.getMailboxCounter());
    },

});
return MailManagerNotification;

});