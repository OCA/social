/* Copyright 2018 David Juaneda
 * License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl). */

odoo.define('mail.Chatter.activity', function(require){
    "use strict";

    var chatter = require('mail.Chatter');

    chatter.include({

        events: {
            'click .o_chatter_button_new_message': '_onOpenComposerMessage',
            'click .o_chatter_button_log_note': '_onOpenComposerNote',
            'click .o_chatter_button_schedule_activity': '_onScheduleActivity',
            'click .o_chatter_button_count_activity': '_onCountActivity',
        },

        _onCountActivity: function (event) {
            event.preventDefault();
            var self = this;
            this._rpc({
                    model: self.record.model,
                    method: 'redirect_to_activities',
                    args: [[]],
                    kwargs: {'id':self.record.res_id,
                             'model':self.record.model},
                    context: this.record.getContext(),
            }).then(function(action) {
                return self.do_action(action);
            });
        },

    });
});
