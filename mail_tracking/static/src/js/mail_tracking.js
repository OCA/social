/* Copyright 2016 Antonio Espinosa - <antonio.espinosa@tecnativa.com>
   Copyright 2018 David Vidal - <david.vidal@tecnativa.com>
     License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html). */

odoo.define('mail_tracking.partner_tracking', function (require) {
    "use strict";

    var core = require('web.core');
    var ActionManager = require('web.ActionManager');
    var web_client = require('web.web_client');
    var chat_manager = require('mail.chat_manager');
    var ChatThread = require('mail.ChatThread');
    var Chatter = require('mail.Chatter');
    var ThreadField = require('mail.ThreadField');
    var Bus = require('bus.bus').bus;

    var _t = core._t;


    // chat_manager is a simple dictionary, not an OdooClass
    chat_manager._make_message_super = chat_manager.make_message;
    chat_manager.make_message = function (data) {
        var msg = this._make_message_super(data);
        msg.partner_trackings = data.partner_trackings || [];
<<<<<<< HEAD
=======
        msg.email_cc = data.email_cc || [];
        msg.track_needs_action = data.track_needs_action || false;
>>>>>>> [IMP] mail_tracking: Filter messages with errors
        return msg;
    };
    chat_manager.toggle_tracking_status = function (message_id) {
        return this._rpc({
                model: 'mail.message',
                method: 'toggle_tracking_status',
                args: [[message_id]],
            });
    };

    ChatThread.include({
        events: _.extend(ChatThread.prototype.events, {
            'click .o_mail_action_tracking_partner':
                'on_tracking_partner_click',
            'click .o_mail_action_tracking_status': 'on_tracking_status_click',
            'click .o_thread_message_tracking': 'on_thread_message_tracking_click'
        }),
        _preprocess_message: function () {
            var msg = this._super.apply(this, arguments);
            msg.partner_trackings = msg.partner_trackings || [];
<<<<<<< HEAD
=======
            msg.email_cc = msg.email_cc || [];
            var needs_action = msg.track_needs_action;
            var message_track = _.findWhere(messages_tracked_changes, {
                id: msg.id,
            });
            if (message_track) {
                needs_action = message_track.status;
            }
            msg.track_needs_action = needs_action;
>>>>>>> [IMP] mail_tracking: Filter messages with errors
            return msg;
        },
        on_tracking_partner_click: function (event) {
            var partner_id = this.$el.find(event.currentTarget).data('partner');
            var state = {
                'model': 'res.partner',
                'id': partner_id,
                'title': _t("Tracking partner"),
            };
            event.preventDefault();
            this.action_manager.do_push_state(state);
            var action = {
                type:'ir.actions.act_window',
                view_type: 'form',
                view_mode: 'form',
                res_model: 'res.partner',
                views: [[false, 'form']],
                target: 'current',
                res_id: partner_id,
            };
            this.do_action(action);
        },
        on_tracking_status_click: function (event) {
            var tracking_email_id = $(event.currentTarget).data('tracking');
            var state = {
                'model': 'mail.tracking.email',
                'id': tracking_email_id,
                'title': _t("Message tracking"),
            };
            event.preventDefault();
            this.action_manager.do_push_state(state);
            var action = {
                type:'ir.actions.act_window',
                view_type: 'form',
                view_mode: 'form',
                res_model: 'mail.tracking.email',
                views: [[false, 'form']],
                target: 'new',
                res_id: tracking_email_id,
            };
            this.do_action(action);
        },
        on_thread_message_tracking_click: function (event) {
            var message_id = $(event.currentTarget).data('message-id');
            this.trigger("toggle_tracking_status", message_id);
        },
        init: function (parent, options) {
            this._super.apply(this, arguments);
            this.action_manager = this.findAncestor(function (ancestor) {
                return ancestor instanceof ActionManager;
            });
        },
    });

    /* Propagate toggle tracking event */
    ThreadField.include({
        _toggleTrackingStatus: function (message_id) {
            this.trigger_up('toggle_tracking_status', {
                message_id: message_id,
            });
        },

        start: function () {
            var res = this._super.apply(this, arguments);
            this.thread.on('toggle_tracking_status', this,
                this._toggleTrackingStatus);
            return res;
        },
    });
    web_client.on('toggle_tracking_status', web_client, function (event) {
        chat_manager.toggle_tracking_status(event.data.message_id);
    });

    /* Because "messages" are an isolated object need store new track states
        to apply it when process messages */
    var messages_tracked_changes = [];
    function on_toggle_tracked_notification (notif_data) {
        _.each(notif_data.message_ids, function (msg_id) {
            var message_track = _.findWhere(messages_tracked_changes, {
                id: msg_id,
            });
            if (message_track) {
                message_track.status = notif_data.tracked;
            } else {
                messages_tracked_changes.push({
                    'id': msg_id,
                    'status': notif_data.tracked,
                });
            }
        });
        // Update thread messages
        chat_manager.bus.trigger('update_message', {
            'model': notif_data.model,
            'res_id': notif_data.res_id,
        });
    }
    function on_notification (notifications) {
        _.each(notifications, function (notification) {
            var model = notification[0][1];
            var notif_vals = notification[1];
            if (model === 'res.partner' && notif_vals.type === 'toggle_track') {
                on_toggle_tracked_notification(notif_vals);
            }
        });
    }
    Bus.on('notification', null, on_notification);
});
