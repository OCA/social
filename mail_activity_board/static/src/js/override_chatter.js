/* Copyright 2018 David Juaneda
 * License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl). */
odoo.define('mail.Chatter.activity', function (require) {
    "use strict";

    var chatter = require('mail.Chatter');

    chatter.include({

        events: _.extend({}, chatter.prototype.events, {
            'click .o_chatter_button_list_activity': '_onListActivity',
        }),

        /**
         * Performs the action to redirect to the activities of the object.
         *
         * @private
         */
        _onListActivity: function () {
            this._rpc({
                model: this.record.model,
                method: 'redirect_to_activities',
                args: [[]],
                kwargs: {
                    'id':this.record.res_id,
                    'model':this.record.model,
                },
                context: this.record.getContext(),
            }).then($.proxy(this, "do_action"));
        },

    });
});
