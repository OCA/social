/* Copyright 2020 Tecnativa - Carlos Roca
   License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html). */
odoo.define('mail_history.Manager', function (require) {
    "use strict";

    var Manager = require('mail.Manager');
    var MailManagerNotif = require('mail.Manager.Notification');
    var core = require('web.core');

    var _t = core._t;

    Manager.include({

        /**
         *  Adds the Mailbox history registry
         *
         * @override
         */
        _updateMailboxesFromServer: function () {
            this._super.apply(this, arguments);
            this._addMailbox({
                id: 'history',
                name: _t("History"),
            });
        },
    });

    MailManagerNotif.include({

        /**
         * Adds the read messages to the history mailbox
         *
         * @override
         */
        _handlePartnerMarkAsReadNotification: function (data) {
            var self = this;
            var history = this.getMailbox('history');
            _.each(data.message_ids, function (messageID) {
                var message = _.find(self._messages, function (msg) {
                    return msg.getID() === messageID;
                });
                if (message) {
                    history.addMessage(message, []);
                }
            });
            return this._super.apply(this, arguments);
        },
    });
});
