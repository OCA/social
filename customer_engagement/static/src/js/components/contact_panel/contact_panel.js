/** @odoo-module **/

import {Component, onWillStart, onWillUpdateProps, useState} from "@odoo/owl";
import {useService} from "@web/core/utils/hooks";

export class ContactPanel extends Component {
    static template = "customer_engagement.ContactPanel";
    static props = {
        conversation: {type: Object, optional: true},
        collapsed: {type: Boolean, optional: true},
        onToggleCollapse: {type: Function, optional: true},
        onOpenPartner: {type: Function, optional: true},
    };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            partner: null,
            conversationHistory: [],
            isLoading: false,
            expandedSections: {
                contact: true,
                channels: true,
                history: false,
                notes: false,
            },
        });

        onWillStart(async () => {
            await this.loadPartnerData();
        });

        onWillUpdateProps(async (nextProps) => {
            if (
                nextProps.conversation?.partner_id?.[0] !==
                this.props.conversation?.partner_id?.[0]
            ) {
                await this.loadPartnerData(nextProps.conversation);
            }
        });
    }

    async loadPartnerData(conversation = this.props.conversation) {
        if (!conversation?.partner_id?.[0]) {
            this.state.partner = null;
            this.state.conversationHistory = [];
            return;
        }

        this.state.isLoading = true;

        const partnerId = conversation.partner_id[0];

        // Load partner details
        const [partner] = await this.orm.read(
            "res.partner",
            [partnerId],
            [
                "name",
                "email",
                "phone",
                "mobile",
                "street",
                "city",
                "state_id",
                "country_id",
                "image_128",
                "company_name",
                "function",
                "website",
                "comment",
            ]
        );

        // Load conversation history with this partner
        const history = await this.orm.searchRead(
            "engage.conversation",
            [
                ["partner_id", "=", partnerId],
                ["id", "!=", conversation.id],
            ],
            ["display_name", "channel_type", "stage_id", "create_date", "resolved_at"],
            {order: "create_date desc", limit: 10}
        );

        this.state.partner = partner;
        this.state.conversationHistory = history;
        this.state.isLoading = false;
    }

    get hasPartner() {
        return this.state.partner !== null;
    }

    get partnerName() {
        return this.state.partner?.name || "Unknown Contact";
    }

    get partnerInitials() {
        return this.partnerName
            .split(" ")
            .map((word) => word[0])
            .slice(0, 2)
            .join("")
            .toUpperCase();
    }

    get partnerImage() {
        if (this.state.partner?.image_128) {
            return `data:image/png;base64,${this.state.partner.image_128}`;
        }
        return null;
    }

    get contactInfo() {
        const partner = this.state.partner;
        if (!partner) return [];

        const info = [];

        if (partner.email) {
            info.push({
                icon: "fa-envelope",
                label: "Email",
                value: partner.email,
                type: "email",
            });
        }
        if (partner.phone) {
            info.push({
                icon: "fa-phone",
                label: "Phone",
                value: partner.phone,
                type: "phone",
            });
        }
        if (partner.mobile) {
            info.push({
                icon: "fa-mobile",
                label: "Mobile",
                value: partner.mobile,
                type: "phone",
            });
        }
        if (partner.company_name) {
            info.push({
                icon: "fa-building",
                label: "Company",
                value: partner.company_name,
            });
        }
        if (partner.function) {
            info.push({
                icon: "fa-briefcase",
                label: "Position",
                value: partner.function,
            });
        }
        if (partner.website) {
            info.push({
                icon: "fa-globe",
                label: "Website",
                value: partner.website,
                type: "url",
            });
        }

        return info;
    }

    get address() {
        const partner = this.state.partner;
        if (!partner) return null;

        const parts = [];
        if (partner.street) parts.push(partner.street);
        if (partner.city) parts.push(partner.city);
        if (partner.state_id) parts.push(partner.state_id[1]);
        if (partner.country_id) parts.push(partner.country_id[1]);

        return parts.length > 0 ? parts.join(", ") : null;
    }

    get channelInfo() {
        const conv = this.props.conversation;
        if (!conv) return [];

        const channels = [];
        const channelType = conv.channel_type;

        if (channelType === "whatsapp" && this.state.partner?.mobile) {
            channels.push({
                icon: "fa-whatsapp",
                color: "success",
                label: "WhatsApp",
                value: this.state.partner.mobile,
            });
        }
        if (channelType === "email" && this.state.partner?.email) {
            channels.push({
                icon: "fa-envelope",
                color: "primary",
                label: "Email",
                value: this.state.partner.email,
            });
        }
        if (channelType === "instagram") {
            channels.push({
                icon: "fa-instagram",
                color: "danger",
                label: "Instagram",
                value:
                    "@" +
                    (this.state.partner?.name || "").toLowerCase().replace(/\s+/g, ""),
            });
        }
        if (channelType === "telegram") {
            channels.push({
                icon: "fa-telegram",
                color: "info",
                label: "Telegram",
                value: this.state.partner?.mobile || "",
            });
        }

        return channels;
    }

    toggleSection(section) {
        this.state.expandedSections[section] = !this.state.expandedSections[section];
    }

    formatDate(dateStr) {
        if (!dateStr) return "";
        const date = new Date(dateStr);
        return date.toLocaleDateString();
    }

    getChannelIcon(channelType) {
        const icons = {
            whatsapp: "fa-whatsapp text-success",
            email: "fa-envelope text-primary",
            instagram: "fa-instagram text-danger",
            messenger: "fa-facebook-messenger text-info",
            telegram: "fa-telegram text-info",
            livechat: "fa-comments text-warning",
            api: "fa-code text-secondary",
        };
        return icons[channelType] || "fa-question text-muted";
    }

    onOpenPartnerClick() {
        if (this.props.onOpenPartner && this.state.partner) {
            this.props.onOpenPartner(this.state.partner.id);
        } else if (this.state.partner) {
            this.action.doAction({
                type: "ir.actions.act_window",
                res_model: "res.partner",
                res_id: this.state.partner.id,
                views: [[false, "form"]],
                target: "current",
            });
        }
    }

    onConversationClick(conversation) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "engage.conversation",
            res_id: conversation.id,
            views: [[false, "form"]],
            target: "current",
        });
    }
}
