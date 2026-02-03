/** @odoo-module **/

import {Component} from "@odoo/owl";

export class ChannelBadge extends Component {
    static template = "customer_engagement.ChannelBadge";
    static props = {
        channel: {type: String, optional: true},
        size: {type: String, optional: true}, // "sm", "md", "lg"
    };

    get channelConfig() {
        const configs = {
            whatsapp: {icon: "fa-whatsapp", color: "success", label: "WhatsApp"},
            email: {icon: "fa-envelope", color: "primary", label: "Email"},
            instagram: {icon: "fa-instagram", color: "danger", label: "Instagram"},
            messenger: {
                icon: "fa-facebook-messenger",
                color: "info",
                label: "Messenger",
            },
            telegram: {icon: "fa-telegram", color: "info", label: "Telegram"},
            livechat: {icon: "fa-comments", color: "warning", label: "Live Chat"},
            api: {icon: "fa-code", color: "secondary", label: "API"},
        };
        return (
            configs[this.props.channel] || {
                icon: "fa-question",
                color: "secondary",
                label: this.props.channel || "Unknown",
            }
        );
    }

    get iconClass() {
        return `fa ${this.channelConfig.icon}`;
    }

    get badgeClass() {
        const size = this.props.size || "sm";
        const sizeClass = size === "sm" ? "badge-sm" : size === "lg" ? "badge-lg" : "";
        return `o_channel_badge text-${this.channelConfig.color} ${sizeClass}`;
    }

    get tooltip() {
        return this.channelConfig.label;
    }
}
