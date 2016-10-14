/* © 2016 Antonio Espinosa - <antonio.espinosa@tecnativa.com>
     License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html). */

odoo.define('mail_tracking.partner_tracking', function(require){
"use strict";

var core = require('web.core');
var session = require('web.session');
var Model = require('web.Model');
var ActionManager = require('web.ActionManager');
var chat_manager = require('mail.chat_manager');
var ChatThread = require('mail.ChatThread');
var Chatter = require('mail.Chatter');

var _t = core._t;
var MessageModel = new Model('mail.message', session.context);

// chat_manager is a simple dictionary, not an OdooClass
chat_manager._make_message_super = chat_manager.make_message;
chat_manager.make_message = function(data) {
    var msg = this._make_message_super(data);
    msg.partner_trackings = data.partner_trackings || [];
    return msg;
};

ChatThread.include({
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
    bind_events: function () {
        this.$el.on('click', '.o_mail_action_tracking_partner',
                    this.on_tracking_partner_click);
        this.$el.on('click', '.o_mail_action_tracking_status',
                    this.on_tracking_status_click);
    },
    init: function (parent, options) {
        this._super.apply(this, arguments);
        this.action_manager = this.findAncestor(function(ancestor){
            return ancestor instanceof ActionManager;
        });
    },
    start: function () {
        this._super();
        this.bind_events();
    },
    render: function(messages, options) {
        var self = this, render_super = this._super,
            msgs = {},
            msg_ids = [];
        // Update trackings (async) each time we re-render thread
        _.each(messages, function (message) {
            msgs[message.id] = message;
            msg_ids.push(message.id);
        });
        MessageModel.call('tracking_status', [msg_ids]).then(function (trackings) {
            _.each(trackings, function (tracking, id) {
                msgs[id].partner_trackings = tracking;
            });
            render_super.apply(self, [messages, options]);
        });
    },

});

}); // odoo.define
