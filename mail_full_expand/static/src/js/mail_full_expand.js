/* Copyright 2014-2015 Grupo ESOC <http://www.grupoesoc.es>
 * License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
 */
odoo.define('mail_full_expand.expand', function (require) {
    "use strict";

    var ThreadWidget = require('mail.widget.Thread');

    ThreadWidget.include({
        events: _.defaults({
            "click .o_full_expand": "_onClickMessageFullExpand",
        }, ThreadWidget.prototype.events),

        _onClickMessageFullExpand: function (event) {
            // Get the action data and execute it to open the full view
            var do_action = this.do_action,
                msg_id = $(event.currentTarget).data('message-id');

            this._rpc({
                route: "/web/action/load",
                params: {
                    action_id: "mail_full_expand.mail_message_action",
                },
            })
                .then(function (action) {
                    action.res_id = msg_id;
                    do_action(action);
                });
        },
    });

});
