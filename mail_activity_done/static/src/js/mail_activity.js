// Copyright 2018-20 ForgeFlow <http://www.forgeflow.com>
// License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

odoo.define("mail.Activity.done", function (require) {
    "use strict";

    var mailUtils = require("mail.utils");
    var core = require("web.core");
    var time = require("web.time");
    var mail_activity = require("mail.Activity");

    var QWeb = core.qweb;
    var _t = core._t;

    // We are forced here to override the method, as there is no possibility
    // to inherit it.
    var setDelayLabel = function (activities) {
        var today = moment().startOf("day");
        _.each(activities, function (activity) {
            var to_display = "";
            var deadline = moment(activity.date_deadline).startOf("day");
            // On next line, true means no rounding
            var diff = deadline.diff(today, "days", true);
            if (diff === 0) {
                to_display = _t("Today");
            } else if (diff < 0) {
                // This block is for overdue
                // eslint-disable-line no-lonely-if
                if (diff === -1) {
                    to_display = _t("Yesterday");
                } else {
                    to_display = _.str.sprintf(_t("%d days overdue"), Math.abs(diff));
                }
                // This block is for due
            } else if (diff === 1) {
                // eslint-disable-line no-lonely-if
                to_display = _t("Tomorrow");
            } else {
                to_display = _.str.sprintf(_t("Due in %d days"), Math.abs(diff));
            }
            activity.label_delay = to_display;
        });
        // We do not want to show the activities that have been completed.
        var open_activities = _.filter(activities, function (activity) {
            return activity.done !== true;
        });
        return open_activities;
    };

    mail_activity.include({
        /**
         * @override
         * @private
         */
        _render: function () {
            _.each(this._activities, function (activity) {
                var note = mailUtils.parseAndTransform(
                    activity.note || "",
                    mailUtils.inline
                );
                var is_blank = /^\s*$/.test(note);
                if (is_blank) {
                    activity.note = "";
                } else {
                    activity.note = mailUtils.parseAndTransform(
                        activity.note,
                        mailUtils.addLink
                    );
                }
            });
            var activities = setDelayLabel(this._activities);
            if (activities.length) {
                var nbActivities = _.countBy(activities, "state");
                this.$el.html(
                    QWeb.render("mail.activity_items", {
                        activities: activities,
                        nbPlannedActivities: nbActivities.planned,
                        nbTodayActivities: nbActivities.today,
                        nbOverdueActivities: nbActivities.overdue,
                        dateFormat: time.getLangDateFormat(),
                        datetimeFormat: time.getLangDatetimeFormat(),
                    })
                );
            } else {
                this.$el.empty();
            }
        },
    });
});
