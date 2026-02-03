/** @odoo-module **/

import {Component, useState} from "@odoo/owl";

export class ChatHeader extends Component {
    static template = "customer_engagement.ChatHeader";
    static props = {
        conversation: {type: Object},
        isAssignedToMe: {type: Boolean},
        isUnassigned: {type: Boolean},
        onAssign: {type: Function},
        onStatusChange: {type: Function},
        onOpenForm: {type: Function},
        onAddLabel: {type: Function, optional: true},
    };

    setup() {
        this.state = useState({
            showStatusMenu: false,
            showMoreMenu: false,
        });
    }

    get partnerName() {
        const conv = this.props.conversation;
        if (conv.partner_id && conv.partner_id[1]) {
            return conv.partner_id[1];
        }
        return "Unknown Contact";
    }

    get channelType() {
        return this.props.conversation.channel_type;
    }

    get channelIcon() {
        const icons = {
            whatsapp: "fa-whatsapp text-success",
            email: "fa-envelope text-primary",
            instagram: "fa-instagram text-danger",
            messenger: "fa-facebook-messenger text-info",
            telegram: "fa-telegram text-info",
            livechat: "fa-comments text-warning",
            api: "fa-code text-secondary",
        };
        return icons[this.channelType] || "fa-question text-muted";
    }

    get stageCode() {
        const conv = this.props.conversation;
        return conv.stage_code || "";
    }

    get statusOptions() {
        return [
            {code: "open", label: "Open", icon: "fa-folder-open", color: "primary"},
            {code: "pending", label: "Pending", icon: "fa-clock-o", color: "warning"},
            {code: "resolved", label: "Resolved", icon: "fa-check", color: "success"},
            {code: "closed", label: "Closed", icon: "fa-times", color: "secondary"},
        ];
    }

    toggleStatusMenu() {
        this.state.showStatusMenu = !this.state.showStatusMenu;
        this.state.showMoreMenu = false;
    }

    toggleMoreMenu() {
        this.state.showMoreMenu = !this.state.showMoreMenu;
        this.state.showStatusMenu = false;
    }

    closeMenus() {
        this.state.showStatusMenu = false;
        this.state.showMoreMenu = false;
    }

    onAssignClick() {
        this.props.onAssign();
    }

    onStatusClick(statusCode) {
        this.props.onStatusChange(statusCode);
        this.closeMenus();
    }

    onOpenFormClick() {
        this.props.onOpenForm();
    }

    onAddLabelClick() {
        if (this.props.onAddLabel) {
            this.props.onAddLabel();
        }
        this.closeMenus();
    }
}
