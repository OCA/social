//-*- coding: utf-8 -*-
//© 2017-2018 Therp BV <http://therp.nl>
//License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

odoo.define('mail.Activity', function(require)
{
    "use strict";
    var Chatter = require('mail.Chatter');
    var kanban_widgets = require('web_kanban.widgets');
    var Model = require('web.Model');
    var form_common = require('web.form_common');
    var core = require('web.core');
    var time = require('web.time');
    var _t = core._t;
    Chatter.include({
        init: function() {
            this._super.apply(this, arguments);
            this.schedule_activity_btn = !!this.view.fields.activity_ids;
        },
        start: function() {
            this.$('button.o_chatter_button_schedule_activity').click(
                this.proxy('_onScheduleActivity')
            );
            this.activity = this.view.fields.activity_ids;
            if(this.activity) {
                this.$('.o_chatter_topbar').after(this.activity.$el);
            }
            return this._super.apply(this, arguments);
        },
        _onScheduleActivity: function() {
            return this.view.fields.activity_ids._scheduleActivity(false);
        },
    });

    /**
     * Set the 'label_delay' entry in activity data according to the deadline date
     * @param {Array} activities list of activity Object
     * @return {Array} : list of modified activity Object
     */
    var setDelayLabel = function(activities) {
        var today = moment().startOf('day');
        _.each(activities, function(activity){
            var to_display = '';
            var deadline = moment(activity.date_deadline + ' 00:00:00');
            var diff = deadline.diff(today, 'days', true); // true means no rounding
            if(diff === 0){
                to_display = _t('Today');
            }else{
                if(diff < 0){ // overdue
                    if(diff === -1){
                        to_display = _t('Yesterday');
                    }else{
                        to_display = _.str.sprintf(_t('%d days overdue'), Math.abs(diff));
                    }
                }else{ // due
                    if(diff === 1){
                        to_display = _t('Tomorrow');
                    }else{
                        to_display = _.str.sprintf(_t('Due in %d days'), Math.abs(diff));
                    }
                }
            }
            activity.label_delay = to_display;
        });
        return activities;
    };

    var AbstractActivityField = form_common.AbstractField.extend({
        _scheduleActivity: function (id, previous_activity_type_id, callback) {
            var self = this,
                action = {
                type: 'ir.actions.act_window',
                res_model: 'mail.activity',
                view_mode: 'form',
                view_type: 'form',
                views: [[false, 'form']],
                target: 'new',
                context: {
                    default_res_id: this.view.datarecord.id,
                    default_res_model: this.view.dataset.model,
                    default_previous_activity_type_id:
                    previous_activity_type_id || false,
                },
                res_id: id || false,
            };
            return this.do_action(action, {
                on_close: function() {
                    if(callback) {
                        callback();
                    }
                    return self.field_manager.reload();
                },
            });
        },
    });

    var Activity = AbstractActivityField.extend({
        className: 'o_mail_activity',
        custom_events: {
            reload_mail_fields: '_onReloadMailFields',
        },
        events: {
            'click .o_activity_edit': '_onEditActivity',
            'click .o_activity_unlink': '_onUnlinkActivity',
            'click .o_activity_done': '_onMarkActivityDone',
        },
        render_value: function() {
            return $.when(
                this._super.apply(this, arguments),
                this._readActivities()
            ).then(this.proxy('_render_value'));
        },
        _render_value: function() {
            var activities = setDelayLabel(this.activities);
            if (activities.length) {
                var nbActivities = _.countBy(activities, 'state');
                this.$el.html(core.qweb.render('mail.activity_items', {
                    activities: activities,
                    nbPlannedActivities: nbActivities.planned,
                    nbTodayActivities: nbActivities.today,
                    nbOverdueActivities: nbActivities.overdue,
                }));
            } else {
                this.$el.empty();
            }
        },
        _readActivities: function() {
            var self = this;
            return new Model('mail.activity')
            .query([])
            .filter([['id', 'in', this.get('value')]])
            .all()
            .then(function(activities) {
                self.activities = activities;
            });
        },
        // handlers
        _onEditActivity: function (event, options) {
            event.preventDefault();
            var self = this;
            var activity_id = $(event.currentTarget).data('activity-id');
            var action = _.defaults(options || {}, {
                type: 'ir.actions.act_window',
                res_model: 'mail.activity',
                view_mode: 'form',
                view_type: 'form',
                views: [[false, 'form']],
                target: 'new',
                context: {
                    default_res_id: this.view.datarecord.id,
                    default_res_model: this.view.dataset.model,
                },
                res_id: activity_id,
            });
            return this.do_action(action, {
                on_close: function () {
                    return self.field_manager.reload();
                },
            });
        },
        _onUnlinkActivity: function (event, options) {
            event.preventDefault();
            var activity_id = $(event.currentTarget).data('activity-id');
            options = _.defaults(options || {}, {
                model: 'mail.activity',
                args: [[activity_id]],
            });
            return new Model('mail.activity')
            .call('unlink', [activity_id])
            .then(this.render_value.bind(this));
        },
    });
    core.form_widget_registry.add('mail_activity', Activity);

    return Activity;

});
