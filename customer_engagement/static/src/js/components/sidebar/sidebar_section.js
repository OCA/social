/** @odoo-module **/

import {Component} from "@odoo/owl";

export class SidebarSection extends Component {
    static template = "customer_engagement.SidebarSection";
    static props = {
        title: {type: String},
        icon: {type: String, optional: true},
        expanded: {type: Boolean},
        onToggle: {type: Function},
        slots: {type: Object, optional: true},
    };

    toggle() {
        this.props.onToggle();
    }
}
