odoo.define('web_kanban_activity.widget', function (require) {
"use strict";

var core = require('web.core');
var kanban_widgets = require('web_kanban.widgets');
var Model = require('web.Model');
var AbstractField = kanban_widgets.AbstractField;
var fields_registry = kanban_widgets.registry;
var _t = core._t;
var time = require('web.time');

/**
 * Set the 'label_delay' entry in activity data according to the deadline date
 * @param {Array} activities list of activity Object
 * @return {Array} : list of modified activity Object
 */
var setDelayLabel = function(activities){
    var today = moment().startOf('day');
    _.each(activities, function(activity){
        var to_display = '';
        var diff = activity.date_deadline.diff(today, 'days', true); // true means no rounding
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

var KanbanActivity = AbstractField.extend({

    events: {
        'click .o_activity_btn': '_onButtonClicked',
        'click .o_schedule_activity': '_onScheduleActivity',
    },

    init: function (parent, name, record) {
        this._super.apply(this, arguments);
    },
    start: function() {
        this.display_field();
        return this._super();
    },

    display_field: function() {
        this.$el.html(core.qweb.render("mail.KanbanActivity"));
    },
    // private
    _reload: function () {
        this.trigger_up('reload', {db_id: this.record_id});
    },
    _renderDropdown: function () {
        var self = this;
        var session = require('web.session');
        this.$('.o_activity').html(core.qweb.render("mail.KanbanActivityLoading"));
        return self._readActivities().then(function (activities) {
            self.$('.o_activity').html(core.qweb.render("mail.KanbanActivityDropdown", {
                records: _.groupBy(setDelayLabel(activities), 'state'),
                uid: session.uid,
            }));
        });
    },
    _scheduleActivity: function (id, previous_activity_type_id) {
        var self = this,
            action = {
            type: 'ir.actions.act_window',
            res_model: 'mail.activity',
            view_mode: 'form',
            view_type: 'form',
            views: [[false, 'form']],
            target: 'new',
            context: {},
            res_id: id || false,
        };
        this.do_action(action);
    },
    _readActivities: function() {
        var self = this;
        return new Model('mail.activity')
        .query([])
        .filter([['id', 'in', this.get('value')]])
        .all()
        .then(function(activities) {
            // convert create_date and date_deadline to moments
            _.each(activities, function (activity) {
                activity.create_date = moment(time.auto_str_to_date(activity.create_date));
                activity.date_deadline = moment(time.auto_str_to_date(activity.date_deadline));
            });

            // sort activities by due date
            activities = _.sortBy(activities, 'date_deadline');
            return activities;
        });
    },
    _onScheduleActivity: function (event) {
        var activity_id = $(event.currentTarget).data('activity-id') || false;
        return this._scheduleActivity(activity_id, false);
    },
    // handlers
    _onButtonClicked: function (event) {
        event.preventDefault();
        if (!this.$el.hasClass('open')) {
            this._renderDropdown();
        }
    },
});

fields_registry.add("kanban_activity", KanbanActivity);

});
