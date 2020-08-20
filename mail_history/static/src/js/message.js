/* Copyright 2020 Tecnativa - Carlos Roca
   License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html). */
odoo.define('mail_history.Message', function (require) {
    "use strict";

    var Message = require('mail.model.Message');
    var session = require('web.session');

    Message.include({

        /**
         * Take the historyPartnerIDs that have to be added to History Mailbox
         *
         * @override
         */
        init: function (parent, data) {
            this._historyPartnerIDs = data.history_partner_ids || [];
            return this._super.apply(this, arguments);
        },

        /**
         * Process the mailbox History with the historyPartnerIDs
         *
         * @override
         */
        _processMailboxes: function () {
            if (_.contains(this._historyPartnerIDs, session.partner_id)) {
                this._setHistory(true);
            }
            return this._super.apply(this, arguments);
        },

        /*
         * Set whether the message is history or not.
         * If it is history, the message is moved to the "History" mailbox.
         * Note that this function only applies it locally, the server
         * is not aware
         *
         * @private
         * @param {boolean} history if set, the message is history
         */
        _setHistory: function (history) {
            if (history) {
                this._addThread('mailbox_history');
            } else {
                this.removeThread('mailbox_history');
            }
        },
    });
});
