/** @odoo-module **/

import {Component} from "@odoo/owl";

export class LabelPills extends Component {
    static template = "customer_engagement.LabelPills";
    static props = {
        labels: {type: Array, optional: true},
        maxVisible: {type: Number, optional: true},
        onRemove: {type: Function, optional: true},
    };

    get hasLabels() {
        return (
            this.props.labels &&
            this.props.labels.length > 0 &&
            typeof this.props.labels[0] === "object"
        );
    }

    get maxLabels() {
        return this.props.maxVisible || 3;
    }

    get visibleLabels() {
        return this.props.labels.slice(0, this.maxLabels);
    }

    get hiddenCount() {
        return Math.max(0, this.props.labels.length - this.maxLabels);
    }

    getLabelClass(label) {
        const colorIndex = label.color || 0;
        return `o_tag o_tag_color_${colorIndex}`;
    }

    onRemoveClick(label, ev) {
        ev.stopPropagation();
        if (this.props.onRemove) {
            this.props.onRemove(label);
        }
    }
}
