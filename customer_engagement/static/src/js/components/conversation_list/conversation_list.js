/** @odoo-module **/

import {Component, useState} from "@odoo/owl";
import {ConversationCard} from "./conversation_card";

export class ConversationList extends Component {
    static template = "customer_engagement.ConversationList";
    static components = {ConversationCard};
    static props = {
        conversations: {type: Array},
        selectedId: {type: [Number, Boolean], optional: true},
        isLoading: {type: Boolean},
        filter: {type: String, optional: true},
        onSelect: {type: Function},
        onFilterChange: {type: Function},
        onSearch: {type: Function, optional: true},
    };

    setup() {
        this.state = useState({
            searchQuery: "",
            activeTab: this.props.filter || "all",
        });
    }

    get tabs() {
        return [
            {key: "mine", label: "Mine"},
            {key: "unassigned", label: "Unassigned"},
            {key: "all", label: "All"},
        ];
    }

    get filteredConversations() {
        let conversations = this.props.conversations;
        if (this.state.searchQuery) {
            const query = this.state.searchQuery.toLowerCase();
            conversations = conversations.filter(
                (conv) =>
                    (conv.display_name &&
                        conv.display_name.toLowerCase().includes(query)) ||
                    (conv.subject && conv.subject.toLowerCase().includes(query)) ||
                    (conv.partner_id &&
                        conv.partner_id[1] &&
                        conv.partner_id[1].toLowerCase().includes(query))
            );
        }
        return conversations;
    }

    onSearchInput(ev) {
        this.state.searchQuery = ev.target.value;
        if (this.props.onSearch) {
            this.props.onSearch(this.state.searchQuery);
        }
    }

    onTabClick(tab) {
        this.state.activeTab = tab;
        this.props.onFilterChange(tab);
    }

    onConversationSelect(conversation) {
        this.props.onSelect(conversation);
    }

    isSelected(conversation) {
        return this.props.selectedId === conversation.id;
    }

    isActiveTab(tab) {
        return this.state.activeTab === tab;
    }
}
