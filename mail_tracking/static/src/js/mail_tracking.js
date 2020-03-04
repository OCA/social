/* Copyright 2016 Antonio Espinosa - <antonio.espinosa@tecnativa.com>
   Copyright 2018 David Vidal - <david.vidal@tecnativa.com>
     License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html). */

odoo.define('mail_tracking.partner_tracking', function (require) {
    "use strict";

    var core = require('web.core');
    var ActionManager = require('web.ActionManager');
    var AbstractMessage = require('mail.model.AbstractMessage');
    var Message = require('mail.model.Message');
    var ThreadWidget = require('mail.widget.Thread');

    var _t = core._t;

    AbstractMessage.include({

        /**
         * Messages do not have any PartnerTrackings.
         *
         * @returns {Boolean}
         */
        hasPartnerTrackings: function () {
            return false;
        },

        /**
         * Messages do not have any email Cc values.
         *
         * @returns {Boolean}
         */
        hasEmailCc: function () {
            return false;
        },
    });

    Message.include({
        init: function (parent, data) {
            this._super.apply(this, arguments);
            this._partnerTrackings = data.partner_trackings || [];
            this._emailCc = data.email_cc || [];
            this._trackNeedsAction = data.track_needs_action || false;
        },

        /**
         * State whether this message contains some PartnerTrackings values
         *
         * @override
         * @returns {Boolean}
         */
        hasPartnerTrackings: function () {
            return _.some(this._partnerTrackings);
        },

        /**
         * State whether this message contains some email Cc values
         *
         * @returns {Boolean}
         */
        hasEmailCc: function () {
            return _.some(this._emailCc);
        },

        /**
         * Get the PartnerTrackings values of this message
         * If this message has no PartnerTrackings values, returns []
         *
         * @override
         * @returns {Object[]}
         */
        getPartnerTrackings: function () {
            if (!this.hasPartnerTrackings()) {
                return [];
            }
            return this._partnerTrackings;
        },

        /**
         * Get the email Cc values of this message
         * If this message has no email Cc values, returns []
         *
         * @returns {Array}
         */
        getEmailCc: function () {
            if (!this.hasEmailCc()) {
                return [];
            }
            return this._emailCc;
        },

        /**
         * Check if the email is an Cc
         * If this message has no email Cc values, returns false
         *
         * @param {String} email
         * @returns {Boolean}
         */
        isEmailCc: function (email) {
            if (!this.hasEmailCc()) {
                return false;
            }
            return _.some(this._emailCc, function (item) {
                return item[0] === email;
            });
        },

        toggleTrackingStatus: function () {
            return this._rpc({
                model: 'mail.message',
                method: 'toggle_tracking_status',
                args: [[this.id]],
            });
        },
    });

    ThreadWidget.include({
        events: _.extend(ThreadWidget.prototype.events, {
            'click .o_mail_action_tracking_partner':
                'on_tracking_partner_click',
            'click .o_mail_action_tracking_status': 'on_tracking_status_click',
        }),
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
        init: function () {
            this._super.apply(this, arguments);
            this.action_manager = this.findAncestor(function (ancestor) {
                return ancestor instanceof ActionManager;
            });
        },
    });
});
