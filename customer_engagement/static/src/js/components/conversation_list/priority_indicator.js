/** @odoo-module **/

import {Component} from "@odoo/owl";

export class PriorityIndicator extends Component {
    static template = "customer_engagement.PriorityIndicator";
    static props = {
        priority: {type: String},
        showLabel: {type: Boolean, optional: true},
    };

    get priorityConfig() {
        const configs = {
            0: {icon: "fa-arrow-down", color: "secondary", label: "Low"},
            1: {icon: "fa-minus", color: "info", label: "Normal"},
            2: {icon: "fa-arrow-up", color: "warning", label: "High"},
            3: {icon: "fa-exclamation", color: "danger", label: "Urgent"},
        };
        return configs[this.props.priority] || configs["1"];
    }

    get iconClass() {
        return `fa ${this.priorityConfig.icon} text-${this.priorityConfig.color}`;
    }

    get indicatorClass() {
        return `o_priority_indicator priority-${this.props.priority}`;
    }
}
