/* Copyright 2019 Alexandre Díaz
   License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html). */
odoo.define('mail_tracking.FailedMessage', function (require) {
    "use strict";

    var ChatAction = require('mail.chat_client_action');
    var AbstractField = require('web.AbstractField');
    var BasicModel = require('web.BasicModel');
    var BasicView = require('web.BasicView');
    var Chatter = require('mail.Chatter');
    var utils = require('mail.utils');
    var chat_manager = require('mail.chat_manager');
    var core = require('web.core');
    var field_registry = require('web.field_registry');
    var time = require('web.time');
    var session = require('web.session');
    var config = require('web.config');
    var bus = require('bus.bus').bus;

    var QWeb = core.qweb;
    var _t = core._t;


    /* DISCUSS */
    // Notification handlers
    function on_notification (notifications) {
        _.each(notifications, function (notification) {
            var model = notification[0][1];
            var data = notification[1];
            if (model === 'res.partner' && data.type === 'failed_updated') {
                // Update failed messages
                var fake_message = {
                    'id': data.id,
                    'is_failed': data.status,
                };
                core.bus.trigger('force_update_message', fake_message);
            }
        });
    }

    var failed_counter = 0;
    var is_channel_failed_outdated = false;
    ChatAction.include({
        events: _.extend({}, ChatAction.prototype.events, {
            'click .o_failed_message_retry': '_onRetryFailedMessage',
            'click .o_failed_message_reviewed': '_onMarkFailedMessageReviewed',
        }),
        init: function () {
            this._super.apply(this, arguments);
            bus.on('notification', null, on_notification);
            // HACK: Custom event to update messsages
            core.bus.on('force_update_message', this, function (data) {
                is_channel_failed_outdated = true;
                this._onMessageUpdated(data);
                this.throttledUpdateChannels();
            });
        },

        _renderSidebar: function (options) {
            options.failed_counter = chat_manager.get_failed_counter();
            return this._super.apply(this, arguments);
        },
        _onMessageUpdated: function (message, type) {
            var self = this;
            var current_channel_id = this.channel.id;
            // HACK: break inheritance because can't override properly
            if (current_channel_id === "channel_failed" &&
                !message.is_failed) {
                chat_manager.get_messages({
                    channel_id: this.channel.id,
                    domain: this.domain,
                }).then(function (messages) {
                    var options = self._getThreadRenderingOptions(messages);
                    self.thread.remove_message_and_render(
                        message.id, messages, options).then(function () {
                        self._updateButtonStatus(messages.length === 0, type);
                    });
                });
            } else {
                this._super.apply(this, arguments);
            }
        },
        _updateChannels: function () {
            var self = this;
            // HACK: break inheritance because can't override properly
            if (this.channel.id === "channel_failed") {
                var $sidebar = this._renderSidebar({
                    active_channel_id:
                        this.channel ? this.channel.id: undefined,
                    channels: chat_manager.get_channels(),
                    needaction_counter: chat_manager.get_needaction_counter(),
                    starred_counter: chat_manager.get_starred_counter(),
                    failed_counter: chat_manager.get_failed_counter(),
                });
                this.$(".o_mail_chat_sidebar").html($sidebar.contents());
                _.each(['dm', 'public', 'private'], function (type) {
                    var $input = self.$(
                        '.o_mail_add_channel[data-type=' + type + '] input');
                    self._prepareAddChannelInput($input, type);
                });
            } else {
                this._super.apply(this, arguments);
            }

            // FIXME: Because can't refresh "channel_failed" we add a flag
            // to indicate that the data is outdated
            var refresh_elm = this.$(
                ".o_mail_chat_sidebar .o_mail_failed_message_refresh");
            refresh_elm.click(function (event) {
                event.preventDefault();
                event.stopPropagation();
                location.reload();
            });
            if (is_channel_failed_outdated) {
                refresh_elm.removeClass('hidden');
            }
        },
        _getThreadRenderingOptions: function () {
            var values = this._super.apply(this, arguments);
            if (this.channel.id === "channel_failed") {
                values.display_reply_icon = false;
                values.display_retry_button = true;
                values.display_reviewed_button = true;
            }
            return values;
        },

        _openComposer: function (context) {
            var failed_msg = chat_manager.get_message(context.message_id);
            this.do_action({
                type: 'ir.actions.act_window',
                res_model: 'mail.compose.message',
                view_mode: 'form',
                view_type: 'form',
                views: [[false, 'form']],
                target: 'new',
                context: context,
            }, {
                on_close: function () {
                    chat_manager.bus.trigger('update_message', failed_msg);
                    core.bus.trigger('force_update_message', failed_msg);
                },
            }).then(this.trigger.bind(this, 'close_composer'));
        },

        // Handlers
        _onRetryFailedMessage: function (event) {
            event.preventDefault();
            var message_id = $(event.currentTarget).data('message-id');
            var failed_msg = chat_manager.get_message(message_id);
            // FIXME: Forced to false to ensure hide special buttons because
            // we can't know at this point if the user has sent the mail.
            failed_msg.is_failed = false;
            var failed_partner_ids = _.map(failed_msg.failed_recipients,
                function (item) {
                    return item[0];
                });
            this._openComposer({
                default_body: utils.get_text2html(failed_msg.body),
                default_partner_ids: failed_partner_ids,
                default_is_log: false,
                default_model: failed_msg.model,
                default_res_id: failed_msg.res_id,
                default_composition_mode: 'comment',
                // Omit followers
                default_hide_followers: true,
                mail_post_autofollow: true,
                message_id: message_id,
            });

        },

        _onMarkFailedMessageReviewed: function (event) {
            event.preventDefault();
            var message_id = $(event.currentTarget).data('message-id');
            var failed_msg = chat_manager.get_message(message_id);
            return this._rpc({
                model: 'mail.message',
                method: 'toggle_tracking_status',
                args: [[message_id]],
                context: session.user_context,
            }).then(function (status) {
                var fake_message = {
                    'id': message_id,
                    'is_failed': status,
                };
                failed_msg.is_failed = status;
                chat_manager.bus.trigger('update_message', fake_message);
                core.bus.trigger('force_update_message', fake_message);
            });
        },
    });

    chat_manager.get_failed_counter = function () {
        return failed_counter;
    };

    chat_manager._onMailClientAction_failed_message_super =
        chat_manager._onMailClientAction;
    chat_manager._onMailClientAction = function (result) {
        failed_counter = result.failed_counter;
        return this._onMailClientAction_failed_message_super(result);
    };

    function add_channel_to_message (message, channel_id) {
        message.channel_ids.push(channel_id);
        message.channel_ids = _.uniq(message.channel_ids);
    }

    chat_manager._make_message_failed_message_super = chat_manager.make_message;
    chat_manager.make_message = function (data) {
        var msg = this._make_message_failed_message_super(data);
        function property_descr (channel) {
            return {
                enumerable: true,
                get: function () {
                    return _.contains(msg.channel_ids, channel);
                },
                set: function (bool) {
                    if (bool) {
                        add_channel_to_message(msg, channel);
                    } else {
                        msg.channel_ids = _.without(msg.channel_ids, channel);
                    }
                },
            };
        }

        Object.defineProperties(msg, {
            is_failed: property_descr("channel_failed"),
        });

        msg.is_failed = data.is_failed_message;
        msg.failed_recipients = data.failed_recipients;
        return msg;
    };

    chat_manager._fetchFromChannel_failed_message_super =
        chat_manager._fetchFromChannel;
    chat_manager._fetchFromChannel = function (channel, options) {
        if (channel.id !== "channel_failed") {
            return this._fetchFromChannel_failed_message_super(
                channel, options);
        }

        // HACK: Can't override '_fetchFromChannel' properly to modify the
        // domain, uses context instead and does it in python.
        session.user_context.filter_failed_message = true;
        var res = this._fetchFromChannel_failed_message_super(
            channel, options);
        res.then(function () {
            delete session.user_context.filter_failed_message;
        });
        return res;
    };

    // HACK: Get failed_counter. Because 'chat_manager' call 'start' need call
    // to '/mail/client_action' again with overrided '_onMailClientAction'
    session.is_bound.then(function () {
        var context = _.extend({isMobile: config.device.isMobile},
            session.user_context);
        return session.rpc('/mail/client_action', {context: context});
    }).then(chat_manager._onMailClientAction.bind(chat_manager));


    /* FAILED MESSAGES CHATTER WIDGET */
    // TODO: Use timeFromNow() in v12
    function time_from_now (date) {
        if (moment().diff(date, 'seconds') < 45) {
            return _t("now");
        }
        return date.fromNow();
    }

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
                msg.hour = time_from_now(msg.date);
            });
            return messages;
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
        _markFailedMessageReviewed: function (id) {
            return this._rpc({
                model: 'mail.message',
                method: 'toggle_tracking_status',
                args: [[id]],
                context: this.record.getContext(),
            }).then(function (status) {
                var fake_message = {
                    'id': id,
                    'is_failed': status,
                };
                chat_manager.bus.trigger('update_message', fake_message);
                core.bus.trigger('force_update_message', fake_message);
            });
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
            this.failed_messages = this.record.specialData[this.name] || [];
        },
        _render: function () {
            if (this.failed_messages.length) {
                this.$el.html(QWeb.render(
                    'mail_tracking.failed_message_items', {
                        failed_messages: this.failed_messages,
                        nbFailedMessages: this.failed_messages.length,
                        date_format: time.getLangDateFormat(),
                        datetime_format: time.getLangDatetimeFormat(),
                    }));
            } else {
                this.$el.empty();
            }
        },
        _reset: function (record) {
            this._super.apply(this, arguments);
            this.failed_messages = this.record.specialData[this.name] || [];
            this.res_id = record.res_id;
        },

        _reload: function (fieldsToReload) {
            this.trigger_up('reload_mail_fields', fieldsToReload);
        },

        _openComposer: function (context) {
            var self = this;
            this.do_action({
                type: 'ir.actions.act_window',
                res_model: 'mail.compose.message',
                view_mode: 'form',
                view_type: 'form',
                views: [[false, 'form']],
                target: 'new',
                context: context,
            }, {
                on_close: function () {
                    self._reload({failed_message: true});
                    self.trigger('need_refresh');
                    chat_manager.get_messages({
                        model: self.model,
                        res_id: self.res_id,
                    });
                },
            }).then(this.trigger.bind(this, 'close_composer'));
        },

        // Handlers
        _onRetryFailedMessage: function (event) {
            event.preventDefault();
            var message_id = $(event.currentTarget).data('message-id');
            var failed_msg = _.findWhere(this.failed_messages,
                {'id': message_id});
            var failed_partner_ids = _.map(failed_msg.failed_recipients,
                function (item) {
                    return item[0];
                });
            this._openComposer({
                default_body: utils.get_text2html(failed_msg.body),
                default_partner_ids: failed_partner_ids,
                default_is_log: false,
                default_model: this.model,
                default_res_id: this.res_id,
                default_composition_mode: 'comment',
                // Omit followers
                default_hide_followers: true,
                mail_post_autofollow: true,
                message_id: message_id,
            });

        },

        _onMarkFailedMessageReviewed: function (event) {
            event.preventDefault();
            var message_id = $(event.currentTarget).data('message-id');
            this._markFailedMessageReviewed(message_id).then(
                this._reload.bind(this, {failed_message: true}));
        },
    });

    field_registry.add('mail_failed_message', FailedMessage);

    var mailWidgets = ['mail_failed_message'];
    BasicView.include({
        init: function (viewInfo) {
            this._super.apply(this, arguments);
            // Adds mail_failed_message as valid mail widget
            var fieldsInfo = viewInfo.fieldsInfo[this.viewType];
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
                // Workaround to avoid trigger reload event twice.
                this._super.apply(this, arguments);
            }
        },
    });

    return FailedMessage;

});
