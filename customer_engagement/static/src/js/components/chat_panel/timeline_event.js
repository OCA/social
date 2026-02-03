/** @odoo-module **/

import {Component} from "@odoo/owl";

export class TimelineEvent extends Component {
    static template = "customer_engagement.TimelineEvent";
    static props = {
        event: {type: Object},
    };

    get eventIcon() {
        const type = this.props.event.event_type;
        const icons = {
            created: "fa-plus-circle text-success",
            assigned: "fa-user-plus text-primary",
            unassigned: "fa-user-times text-warning",
            status_change: "fa-exchange text-info",
            label_added: "fa-tag text-primary",
            label_removed: "fa-tag text-muted",
            team_assigned: "fa-users text-primary",
            resolved: "fa-check-circle text-success",
            reopened: "fa-undo text-warning",
            closed: "fa-times-circle text-secondary",
        };
        return icons[type] || "fa-info-circle text-muted";
    }

    get formattedTime() {
        const date = new Date(this.props.event.date);
        return date.toLocaleTimeString(undefined, {
            hour: "2-digit",
            minute: "2-digit",
        });
    }
}
