/** @odoo-module **/

import {Component} from "@odoo/owl";

export class NoteBubble extends Component {
    static template = "customer_engagement.NoteBubble";
    static props = {
        note: {type: Object},
        onPin: {type: Function, optional: true},
        onDelete: {type: Function, optional: true},
    };

    get authorName() {
        const note = this.props.note;
        if (note.author_id && note.author_id[1]) {
            return note.author_id[1];
        }
        return "Unknown";
    }

    get authorInitials() {
        return this.authorName
            .split(" ")
            .map((word) => word[0])
            .slice(0, 2)
            .join("")
            .toUpperCase();
    }

    get formattedTime() {
        const date = new Date(this.props.note.create_date);
        return date.toLocaleTimeString(undefined, {
            hour: "2-digit",
            minute: "2-digit",
        });
    }

    get formattedDate() {
        const date = new Date(this.props.note.create_date);
        return date.toLocaleDateString();
    }

    get isPinned() {
        return this.props.note.is_pinned;
    }

    onPinClick() {
        if (this.props.onPin) {
            this.props.onPin(this.props.note);
        }
    }

    onDeleteClick() {
        if (this.props.onDelete) {
            this.props.onDelete(this.props.note);
        }
    }
}
