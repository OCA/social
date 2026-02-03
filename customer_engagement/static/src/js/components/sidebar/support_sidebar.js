/** @odoo-module **/

import {Component, onWillStart, useState} from "@odoo/owl";
import {useService} from "@web/core/utils/hooks";
import {SidebarSection} from "./sidebar_section";
import {SidebarItem} from "./sidebar_item";

export class SupportSidebar extends Component {
    static template = "customer_engagement.SupportSidebar";
    static components = {SidebarSection, SidebarItem};
    static props = {
        collapsed: {type: Boolean, optional: true},
        activeFilter: {type: String, optional: true},
        activeFolder: {type: Object, optional: true},
        counts: {type: Object},
        onFilterChange: {type: Function},
        onFolderSelect: {type: Function},
        onToggleCollapse: {type: Function, optional: true},
    };

    setup() {
        this.orm = useService("orm");
        this.state = useState({
            folders: [],
            teams: [],
            labels: [],
            channels: [],
            expandedSections: {
                conversations: true,
                folders: true,
                teams: false,
                channels: false,
                labels: false,
            },
        });

        onWillStart(async () => {
            await this.loadSidebarData();
        });
    }

    async loadSidebarData() {
        const [folders, teams, labels] = await Promise.all([
            this.orm.searchRead(
                "support.folder",
                [["active", "=", true]],
                [
                    "name",
                    "code",
                    "icon",
                    "color",
                    "folder_type",
                    "is_system",
                    "conversation_count",
                ],
                {order: "sequence, name"}
            ),
            this.orm.searchRead(
                "support.team",
                [["active", "=", true]],
                ["name", "color", "conversation_count", "member_count"],
                {order: "sequence, name"}
            ),
            this.orm.searchRead(
                "support.conversation.label",
                [["active", "=", true]],
                ["name", "color", "conversation_count"],
                {order: "sequence, name"}
            ),
        ]);

        this.state.folders = folders;
        this.state.teams = teams;
        this.state.labels = labels;
        this.state.channels = this.getChannelOptions();
    }

    getChannelOptions() {
        return [
            {code: "whatsapp", name: "WhatsApp", icon: "fa-whatsapp", color: "success"},
            {code: "email", name: "Email", icon: "fa-envelope", color: "primary"},
            {
                code: "instagram",
                name: "Instagram",
                icon: "fa-instagram",
                color: "danger",
            },
            {
                code: "messenger",
                name: "Messenger",
                icon: "fa-facebook-messenger",
                color: "info",
            },
            {code: "telegram", name: "Telegram", icon: "fa-telegram", color: "info"},
            {
                code: "livechat",
                name: "Live Chat",
                icon: "fa-comments",
                color: "warning",
            },
        ];
    }

    toggleSection(section) {
        this.state.expandedSections[section] = !this.state.expandedSections[section];
    }

    onMainFilterClick(filter) {
        this.props.onFilterChange(filter);
    }

    onFolderClick(folder) {
        this.props.onFolderSelect(folder);
    }

    onTeamClick(team) {
        this.props.onFilterChange("team", team.id);
    }

    onChannelClick(channel) {
        this.props.onFilterChange("channel", channel.code);
    }

    onLabelClick(label) {
        this.props.onFilterChange("label", label.id);
    }

    get systemFolders() {
        return this.state.folders.filter((f) => f.is_system);
    }

    get customFolders() {
        return this.state.folders.filter((f) => !f.is_system);
    }

    isActiveFilter(filter) {
        return this.props.activeFilter === filter;
    }

    isActiveFolder(folder) {
        return this.props.activeFolder && this.props.activeFolder.id === folder.id;
    }
}
