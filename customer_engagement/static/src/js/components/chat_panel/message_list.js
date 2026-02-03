/** @odoo-module **/

import {Component, onMounted, onPatched, useRef} from "@odoo/owl";
import {MessageBubble} from "./message_bubble";
import {NoteBubble} from "./note_bubble";
import {TimelineEvent} from "./timeline_event";

export class MessageList extends Component {
    static template = "customer_engagement.MessageList";
    static components = {MessageBubble, NoteBubble, TimelineEvent};
    static props = {
        timeline: {type: Array},
        currentUserId: {type: Number},
        isLoading: {type: Boolean},
    };

    setup() {
        this.containerRef = useRef("container");

        onMounted(() => {
            this.scrollToBottom();
        });

        onPatched(() => {
            this.scrollToBottom();
        });
    }

    scrollToBottom() {
        const el = this.containerRef.el;
        if (el) {
            el.scrollTop = el.scrollHeight;
        }
    }

    isOutgoing(message) {
        // Check if the message was sent by an internal user
        if (!message.author_id) return false;

        // If author is linked to a user (internal), it's outgoing
        // This is a simplification - in real implementation you'd check user relation
        return message.author_id[0] && message.is_internal_user;
    }

    formatDate(dateStr) {
        if (!dateStr) return "";
        const date = new Date(dateStr);
        return date.toLocaleDateString(undefined, {
            weekday: "short",
            month: "short",
            day: "numeric",
        });
    }

    shouldShowDateSeparator(item, index) {
        if (index === 0) return true;
        const prevItem = this.props.timeline[index - 1];
        const prevDate = new Date(prevItem.date).toDateString();
        const currentDate = new Date(item.date).toDateString();
        return prevDate !== currentDate;
    }
}
