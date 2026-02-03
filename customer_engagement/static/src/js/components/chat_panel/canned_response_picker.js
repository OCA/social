/** @odoo-module **/

import {Component, onWillStart, useState} from "@odoo/owl";
import {useService} from "@web/core/utils/hooks";

export class CannedResponsePicker extends Component {
    static template = "customer_engagement.CannedResponsePicker";
    static props = {
        channelType: {type: String, optional: true},
        teamId: {type: Number, optional: true},
        onSelect: {type: Function},
        onClose: {type: Function},
    };

    setup() {
        this.orm = useService("orm");
        this.state = useState({
            responses: [],
            filteredResponses: [],
            searchQuery: "",
            activeCategory: "all",
            isLoading: true,
        });

        onWillStart(async () => {
            await this.loadResponses();
        });
    }

    get categories() {
        return [
            {key: "all", label: "All"},
            {key: "greeting", label: "Greetings"},
            {key: "closing", label: "Closings"},
            {key: "info", label: "Information"},
            {key: "apology", label: "Apologies"},
            {key: "followup", label: "Follow-ups"},
            {key: "other", label: "Other"},
        ];
    }

    async loadResponses() {
        this.state.isLoading = true;

        const domain = [["active", "=", true]];

        const responses = await this.orm.searchRead(
            "support.canned.response",
            domain,
            ["shortcut", "name", "content", "plain_content", "category", "usage_count"],
            {order: "usage_count desc, sequence"}
        );

        // Filter by channel and team if needed
        this.state.responses = responses.filter((r) => {
            if (r.channel_types && this.props.channelType) {
                const channels = r.channel_types.split(",");
                if (!channels.includes(this.props.channelType)) {
                    return false;
                }
            }
            return true;
        });

        this.filterResponses();
        this.state.isLoading = false;
    }

    filterResponses() {
        let filtered = this.state.responses;

        // Filter by category
        if (this.state.activeCategory !== "all") {
            filtered = filtered.filter((r) => r.category === this.state.activeCategory);
        }

        // Filter by search query
        if (this.state.searchQuery) {
            const query = this.state.searchQuery.toLowerCase();
            filtered = filtered.filter(
                (r) =>
                    r.shortcut.toLowerCase().includes(query) ||
                    r.name.toLowerCase().includes(query) ||
                    (r.plain_content && r.plain_content.toLowerCase().includes(query))
            );
        }

        this.state.filteredResponses = filtered;
    }

    setCategory(category) {
        this.state.activeCategory = category;
        this.filterResponses();
    }

    onSearchInput(ev) {
        this.state.searchQuery = ev.target.value;
        this.filterResponses();
    }

    onResponseClick(response) {
        this.props.onSelect(response);
    }

    onClose() {
        this.props.onClose();
    }

    truncateContent(content, maxLength = 80) {
        if (!content) return "";
        if (content.length <= maxLength) return content;
        return content.substring(0, maxLength) + "...";
    }
}
