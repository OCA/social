/* Copyright 2018 David Juaneda
 * License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl). */

odoo.define('mail.Chatter.activity', function(require){
    "use strict";

    var chatter = require('mail.Chatter');
    var concurrency = require('web.concurrency');
    var core = require('web.core');
    var _t = core._t;
    var QWeb = core.qweb;

    chatter.include({

        events: _.extend({}, chatter.prototype.events, {
            'click .o_chatter_button_list_activity': '_onListActivity',
        }),

        _onListActivity: function (event) {
            event.preventDefault();
            this._rpc({
                    model: this.record.model,
                    method: 'redirect_to_activities',
                    args: [[]],
                    kwargs: {'id':this.record.res_id,
                             'model':this.record.model},
                    context: this.record.getContext(),
            }).then($.proxy(this, "do_action"));
        },
        _formatActivitiesList: function (count){
            var str = '';
            if (count <= 0) {
                str = _t('No activities');
            } else if (count === 1){
                str = _t('One activity');
            } else {
                str = ''+count+' '+_t('activities');
            }
            return str;
        },
        _render: function (def) {
            // the rendering of the chatter is aynchronous: relational data of its fields needs to be
            // fetched (in some case, it might be synchronous as they hold an internal cache).
            // this function takes a deferred as argument, which is resolved once all fields have
            // fetched their data
            // this function appends the fields where they should be once the given deferred is resolved
            // and if it takes more than 500ms, displays a spinner to indicate that it is loading
            var self = this;

            console.log(self.fields.activity);

            var $spinner = $(QWeb.render('Spinner'));
            concurrency.rejectAfter(concurrency.delay(500), def).then(function () {
                $spinner.appendTo(self.$el);
            });
            return def.then(function () {
                if (self.fields.activity) {
                    self.$('.o_list_activity')
                                .html(self.fields.activity.activities.length)
                                .parent().attr("title", self._formatActivitiesList(self.fields.activity.activities.length));

                    self.fields.activity.$el.appendTo(self.$el);

                }
                if (self.fields.followers) {
                    self.fields.followers.$el.appendTo(self.$topbar);
                }
                if (self.fields.thread) {
                    self.fields.thread.$el.appendTo(self.$el);
                }
            }).always($spinner.remove.bind($spinner));
        },

    });
});
