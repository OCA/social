/** @odoo-module **/

import {Component} from "@odoo/owl";

export class SidebarItem extends Component {
    static template = "customer_engagement.SidebarItem";
    static props = {
        label: {type: String},
        icon: {type: String, optional: true},
        count: {type: Number, optional: true},
        color: {type: [Number, String], optional: true},
        active: {type: Boolean, optional: true},
        onClick: {type: Function},
        badge: {type: String, optional: true},
        badgeClass: {type: String, optional: true},
    };

    get iconClass() {
        return this.props.icon ? `fa ${this.props.icon}` : "fa fa-circle";
    }

    get colorClass() {
        if (typeof this.props.color === "number") {
            return `o_tag_color_${this.props.color}`;
        }
        return this.props.color ? `text-${this.props.color}` : "";
    }

    get itemClass() {
        const classes = [
            "o_engage_sidebar_item",
            "d-flex",
            "align-items-center",
            "gap-2",
            "px-3",
            "py-2",
            "cursor-pointer",
        ];
        if (this.props.active) {
            classes.push("active");
        }
        return classes.join(" ");
    }

    onClick() {
        this.props.onClick();
    }
}
