/** @odoo-module **/

import {registerPatch} from "@mail/model/model_core";
import session from "web.session";

registerPatch({
    name: "ActivityGroupView",
    recordMethods: {
        onClickFilterButton(ev) {
            const _super = this._super.bind(this);
            if (this.activityMenuViewOwner.currentFilter === "my") {
                return _super(ev);
            }
            if (this.activityMenuViewOwner.currentFilter === "team") {
                this.activityMenuViewOwner.close();
                const data = _.extend(
                    {},
                    $(ev.currentTarget).data(),
                    $(ev.target).data()
                );
                const context = {};
                if (data.filter === "my") {
                    context.search_default_activities_overdue = 1;
                    context.search_default_activities_today = 1;
                } else {
                    context["search_default_activities_" + data.filter] = 1;
                }
                context.team_activities = true;
                // Necessary because activity_ids of mail.activity.mixin has auto_join
                // So, duplicates are faking the count and "Load more" doesn't show up
                context.force_search_count = 1;
                let domain = [["activity_team_user_ids", "in", [session.uid]]];
                if (data.domain) {
                    domain = domain.concat(data.domain);
                }
                this.env.services.action.doAction(
                    {
                        context,
                        domain,
                        name: data.model_name,
                        res_model: data.res_model,
                        search_view_id: [false],
                        type: "ir.actions.act_window",
                        views: this.activityGroup.irModel.availableWebViews.map(
                            (viewName) => [false, viewName]
                        ),
                    },
                    {
                        clearBreadcrumbs: true,
                    }
                );
            }
        },
    },
});
