/** @odoo-module **/

import {Component} from "@odoo/owl";
import {ChannelBadge} from "./channel_badge";
import {LabelPills} from "./label_pills";
import {PriorityIndicator} from "./priority_indicator";
import {RelativeTime} from "./relative_time";

export class ConversationCard extends Component {
    static template = "customer_engagement.ConversationCard";
    static components = {ChannelBadge, LabelPills, PriorityIndicator, RelativeTime};
    static props = {
        conversation: {type: Object},
        selected: {type: Boolean, optional: true},
        onClick: {type: Function},
    };

    get partnerName() {
        const conv = this.props.conversation;
        if (conv.partner_id && conv.partner_id[1]) {
            return conv.partner_id[1];
        }
        return "Unknown Contact";
    }

    get partnerInitials() {
        const name = this.partnerName;
        return name
            .split(" ")
            .map((word) => word[0])
            .slice(0, 2)
            .join("")
            .toUpperCase();
    }

    get subject() {
        return this.props.conversation.subject || "No subject";
    }

    get stageName() {
        const conv = this.props.conversation;
        if (conv.stage_id && conv.stage_id[1]) {
            return conv.stage_id[1];
        }
        return "";
    }

    get stageCode() {
        // We need stage code for styling - this should be passed from parent
        const conv = this.props.conversation;
        return conv.stage_code || "";
    }

    get assignedAgent() {
        const conv = this.props.conversation;
        if (conv.user_id && conv.user_id[1]) {
            return conv.user_id[1];
        }
        return null;
    }

    get cardClass() {
        const classes = ["o_support_conversation_card"];
        if (this.props.selected) {
            classes.push("selected");
        }
        if (this.props.conversation.unread_message_count > 0) {
            classes.push("unread");
        }
        return classes.join(" ");
    }

    get priorityClass() {
        const priority = this.props.conversation.priority;
        switch (priority) {
            case "3":
                return "priority-urgent";
            case "2":
                return "priority-high";
            default:
                return "";
        }
    }

    onClick() {
        this.props.onClick(this.props.conversation);
    }
}
