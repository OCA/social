/** @odoo-module */

import {ActivityMenu} from "@mail/core/web/activity_menu";
import {patch} from "@web/core/utils/patch";

patch(ActivityMenu.prototype, {
    setup() {
        super.setup();
        this.currentFilter = "my";
    },
    activateFilter(filter_el) {
        this.deactivateButtons();

        filter_el.addClass("active");
        this.currentFilter = filter_el.data("filter");
        this.updateTeamActivitiesContext();
        this.fetchSystrayActivities();
    },
    updateTeamActivitiesContext() {
        var active = false;
        if (this.currentFilter === "team") {
            active = true;
        }
        this.env.services.orm.user.updateContext({team_activities: active});
    },
    onBeforeOpen() {
        this.env.services.orm.user.updateContext({team_activities: false});
        super.onBeforeOpen();
    },

    deactivateButtons() {
        $(".o_filter_nav_item").removeClass("active");
    },
    onClickActivityFilter(filter) {
        this.activateFilter($("." + filter));
    },
});
