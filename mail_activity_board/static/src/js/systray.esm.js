/** @odoo-module **/
import ActivityMenu from "@mail/js/systray/systray_activity_menu";

ActivityMenu.include({
    events: _.extend({}, ActivityMenu.prototype.events, {
        "click .o_all_activities_button": "_onClickOpenAllActivities",
    }),

    _open_boards_activities_domain: function () {
        return {additional_context: {search_default_activities_my: 1}};
    },

    _onClickOpenAllActivities: function () {
        this.do_action(
            "mail_activity_board.open_boards_activities",
            this._open_boards_activities_domain()
        );
    },
});
