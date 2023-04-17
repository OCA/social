/** @odoo-module **/

import {attr} from "@mail/model/model_field";
import {registerPatch} from "@mail/model/model_core";
import session from "web.session";

registerPatch({
    name: "ActivityMenuView",
    fields: {
        currentFilter: attr({
            default: "my",
        }),
        isTeamActive: attr({
            default: false,
        }),
    },
    recordMethods: {
        close() {
            const _super = this._super.bind(this);
            this.activateFilter($(".my_activities"));
            return _super();
        },
        onClickDropdownToggle(ev) {
            const _super = this._super.bind(this);
            this.activateFilter($(".my_activities"));
            return _super(ev);
        },
        deactivateButtons() {
            $(".o_filter_nav_item").removeClass("active");
        },
        updateTeamActivitiesContext() {
            this.update({isTeamActive: this.currentFilter === "team"});
        },
        activateFilter(filter) {
            this.deactivateButtons();
            filter.addClass("active");
            this.update({currentFilter: filter.data("filter")});
            this.updateTeamActivitiesContext();
            this.fetchData();
        },
        onClickActivityFilter(event) {
            event.stopPropagation();
            this.activateFilter($(event.currentTarget));
        },
        /**
         * @override
         */
        async fetchData() {
            const _super = this._super.bind(this);
            if (!this.isTeamActive) {
                return _super();
            }
            const context = _.extend({}, session.user_context, {team_activities: true});
            const data = await this.messaging.rpc({
                model: "res.users",
                method: "systray_get_activities",
                args: [],
                kwargs: {context: context},
            });
            this.update({
                activityGroups: data.map((vals) =>
                    this.messaging.models.ActivityGroup.convertData(vals)
                ),
                extraCount: 0,
            });
        },
    },
});
