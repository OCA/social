//Copyright2018 Eficent <http://www.eficent.com>
//License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

odoo.define('mail.Activity.done', function(require) {
"use strict";
    var core = require('web.core');
    var utils = require('mail.utils');
    var time = require('web.time');
    var mail_activity = require('mail.Activity');

    var QWeb = core.qweb;
    var _t = core._t;

    // We are forced here to override the method, as there is no possibility
    // to inherit it.
    var setDelayLabel = function(activities) {
        var today = moment().startOf('day');
        _.each(activities, function(activity) {
            var to_display = '';
            var deadline = moment(activity.date_deadline).startOf('day');
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
        // We do not want to show the activities that have been completed.
        var open_activities = _.filter(activities, function(activity){
            return activity.done !== true
        });
        return open_activities;
    };

    var Activity = mail_activity.include({

        _render: function () {
            _.each(this.activities, function (activity) {
                if (activity.note) {
                    activity.note = utils.parse_and_transform(activity.note, utils.add_link);
                }
            });
            var activities = setDelayLabel(this.activities);
            if (activities.length) {
                var nbActivities = _.countBy(activities, 'state');
                this.$el.html(QWeb.render('mail.activity_items', {
                    activities: activities,
                    nbPlannedActivities: nbActivities.planned,
                    nbTodayActivities: nbActivities.today,
                    nbOverdueActivities: nbActivities.overdue,
                    date_format: time.getLangDateFormat(),
                    datetime_format: time.getLangDatetimeFormat(),
                }));
            } else {
                this.$el.empty();
            }
        },
    });
});
