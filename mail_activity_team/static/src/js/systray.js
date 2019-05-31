odoo.define('mail_activity_team.systray', function (require) {
    "use strict";

    var systray = require('mail.systray');
    var session = require("web.session");

    systray.ActivityMenu.include({
        events: _.extend({}, systray.ActivityMenu.prototype.events, {
            'click .o_filter_button': 'on_click_filter_button',
        }),
        start: function () {
            this._super.apply(this, arguments);
            this.$filter_buttons = this.$('.o_filter_button');
            this.$my_activities = this.$filter_buttons.first();
            this.filter = 'my';
        },
        on_click_filter_button: function (event) {
            var self = this;

            event.stopPropagation();
            self.$filter_buttons.removeClass('active');
            var $target = $(event.currentTarget);
            $target.addClass('active');
            self.filter = $target.data('filter');
            if (self.filter === 'team') {
                session.user_context = _.extend({}, session.user_context, {
                    'team_activities': true
                });
            }
            else if (self.filter == 'my'){
                session.user_context = _.extend({}, session.user_context, {
                    'team_activities': false,
                });
            }
            self._updateActivityPreview();

        },
        _onActivityFilterClick: function (event) {
            if (this.filter === 'my') {
                this._super.apply(this, arguments);
            }
            if (this.filter === 'team') {
                var data = _.extend(
                    {},
                    $(event.currentTarget).data(),
                    $(event.target).data()
                );
                var context = {};
                if (data.filter === 'my') {
                    context.search_default_activities_overdue = 1;
                    context.search_default_activities_today = 1;
                } else {
                    context['search_default_activities_' + data.filter] = 1;
                }
                this.do_action({
                    type: 'ir.actions.act_window',
                    name: data.model_name,
                    res_model:  data.res_model,
                    views: [[false, 'kanban'], [false, 'form']],
                    search_view_id: [false],
                    domain: [
                        ['activity_team_user_ids', 'in', session.uid]
                     ],
                    context:context,
                });
            }
        },
    });

});
