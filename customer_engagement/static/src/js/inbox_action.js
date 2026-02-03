/** @odoo-module **/

import {Component, onMounted, onWillStart, onWillUnmount, useState} from "@odoo/owl";
import {registry} from "@web/core/registry";
import {useService} from "@web/core/utils/hooks";
import {Layout} from "@web/search/layout";
import {session} from "@web/session";

// Import new components
import {EngageSidebar} from "./components/sidebar/engage_sidebar";
import {ConversationList} from "./components/conversation_list/conversation_list";
import {ChatPanel} from "./components/chat_panel/chat_panel";
import {ContactPanel} from "./components/contact_panel/contact_panel";

class EngageInbox extends Component {
    static template = "customer_engagement.EngageInbox";
    static components = {
        Layout,
        EngageSidebar,
        ConversationList,
        ChatPanel,
        ContactPanel,
    };
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        this.bus = useService("bus_service");

        this.userId = session.uid;
        this.userName = session.name;

        // Determine initial collapsed states based on screen size
        const initialWidth = window.innerWidth;
        const isMobile = initialWidth < 768;
        const isTablet = initialWidth >= 768 && initialWidth < 992;

        this.state = useState({
            // Data
            conversations: [],
            selectedConversation: null,
            messages: [],
            notes: [],

            // Filters
            filter: "all",
            activeFolder: null,
            statusFilter: null,
            channelFilter: null,
            teamFilter: null,
            labelFilter: null,

            // UI State
            isLoading: true,
            isLoadingMessages: false,
            sidebarCollapsed: isMobile || isTablet,
            contactPanelCollapsed: isMobile,
            mobileView: "list", // "list" | "chat" | "contact"

            // Counts
            counts: {
                all: 0,
                mine: 0,
                unassigned: 0,
            },
        });

        this.display = {
            controlPanel: {},
        };

        onWillStart(async () => {
            await Promise.all([this.loadConversations(), this.loadCounts()]);
        });

        onMounted(() => {
            // Poll for new conversations every 30 seconds
            this.pollInterval = setInterval(() => {
                this.loadConversations();
                this.loadCounts();
            }, 30000);

            // Subscribe to bus notifications
            this.subscribeToBusNotifications();

            // Handle window resize for responsive
            this.handleResize();
            window.addEventListener("resize", this.handleResize.bind(this));
        });

        onWillUnmount(() => {
            if (this.pollInterval) {
                clearInterval(this.pollInterval);
            }
            window.removeEventListener("resize", this.handleResize.bind(this));
        });
    }

    handleResize() {
        const width = window.innerWidth;
        if (width < 768) {
            this.state.sidebarCollapsed = true;
            this.state.contactPanelCollapsed = true;
        } else if (width < 992) {
            this.state.sidebarCollapsed = true;
        }
    }

    subscribeToBusNotifications() {
        // Subscribe to conversation updates
        try {
            this.bus.subscribe("engage.conversation", (payload) => {
                if (
                    payload.type === "new_message" &&
                    this.state.selectedConversation?.id === payload.conversation_id
                ) {
                    this.loadMessages(payload.conversation_id);
                }
                this.loadConversations();
                this.loadCounts();
            });
        } catch (e) {
            // Bus service may not be available
            console.debug("Bus notifications not available:", e);
        }
    }

    // ==================== Data Loading ====================

    async loadConversations() {
        this.state.isLoading = true;
        const domain = this.buildDomain();

        try {
            this.state.conversations = await this.orm.searchRead(
                "engage.conversation",
                domain,
                [
                    "uuid",
                    "subject",
                    "display_name",
                    "partner_id",
                    "user_id",
                    "channel_type",
                    "stage_id",
                    "priority",
                    "create_date",
                    "write_date",
                    "label_ids",
                    "team_id",
                    "unread_message_count",
                    "last_message_preview",
                    "last_message_date",
                ],
                {order: "write_date desc", limit: 100}
            );

            // Load stage codes for filtering
            await this.enrichConversationsWithStageCode();
        } catch (e) {
            console.error("Error loading conversations:", e);
            this.notification.add("Failed to load conversations", {type: "danger"});
        }

        this.state.isLoading = false;
    }

    async enrichConversationsWithStageCode() {
        const stageIds = [
            ...new Set(
                this.state.conversations.map((c) => c.stage_id?.[0]).filter(Boolean)
            ),
        ];
        if (stageIds.length === 0) return;

        const stages = await this.orm.searchRead(
            "engage.conversation.stage",
            [["id", "in", stageIds]],
            ["id", "code"]
        );

        const stageCodeMap = {};
        for (const stage of stages) {
            stageCodeMap[stage.id] = stage.code;
        }

        for (const conv of this.state.conversations) {
            if (conv.stage_id) {
                conv.stage_code = stageCodeMap[conv.stage_id[0]] || "";
            }
        }
    }

    async loadCounts() {
        try {
            const userId = this.userId;
            const [allCount, mineCount, unassignedCount] = await Promise.all([
                this.orm.searchCount("engage.conversation", [["closed", "=", false]]),
                this.orm.searchCount("engage.conversation", [
                    ["closed", "=", false],
                    ["user_id", "=", userId],
                ]),
                this.orm.searchCount("engage.conversation", [
                    ["closed", "=", false],
                    ["user_id", "=", false],
                ]),
            ]);
            this.state.counts = {
                all: allCount,
                mine: mineCount,
                unassigned: unassignedCount,
            };
        } catch (e) {
            console.error("Error loading counts:", e);
        }
    }

    buildDomain() {
        let domain = [["closed", "=", false]];

        // Main filter
        if (this.state.filter === "mine") {
            domain.push(["user_id", "=", this.userId]);
        } else if (this.state.filter === "unassigned") {
            domain.push(["user_id", "=", false]);
        }

        // Folder filter (smart folders have their own domain)
        if (
            this.state.activeFolder?.folder_type === "smart" &&
            this.state.activeFolder?.domain
        ) {
            try {
                const folderDomain = JSON.parse(
                    this.state.activeFolder.domain.replace(/'/g, '"')
                );
                domain = [...domain, ...folderDomain];
            } catch (e) {
                console.warn("Invalid folder domain:", e);
            }
        }

        // Status filter
        if (this.state.statusFilter) {
            domain.push(["stage_id.code", "=", this.state.statusFilter]);
        }

        // Channel filter
        if (this.state.channelFilter) {
            domain.push(["channel_type", "=", this.state.channelFilter]);
        }

        // Team filter
        if (this.state.teamFilter) {
            domain.push(["team_id", "=", this.state.teamFilter]);
        }

        // Label filter
        if (this.state.labelFilter) {
            domain.push(["label_ids", "in", this.state.labelFilter]);
        }

        return domain;
    }

    async loadMessages(conversationId) {
        this.state.isLoadingMessages = true;
        try {
            const [messages, notes] = await Promise.all([
                this.orm.searchRead(
                    "mail.message",
                    [
                        ["res_id", "=", conversationId],
                        ["model", "=", "engage.conversation"],
                    ],
                    [
                        "body",
                        "author_id",
                        "date",
                        "message_type",
                        "attachment_ids",
                        "subtype_id",
                    ],
                    {order: "date asc"}
                ),
                this.orm.searchRead(
                    "engage.conversation.note",
                    [["conversation_id", "=", conversationId]],
                    [
                        "content",
                        "author_id",
                        "create_date",
                        "is_pinned",
                        "attachment_ids",
                    ],
                    {order: "create_date asc"}
                ),
            ]);

            // Batch check for internal users (avoid N+1 queries)
            const partnerIds = [
                ...new Set(messages.map((m) => m.author_id?.[0]).filter(Boolean)),
            ];
            const internalPartnerIds = await this.getInternalPartnerIds(partnerIds);

            // Mark messages as internal/external
            for (const msg of messages) {
                msg.is_internal_user = internalPartnerIds.has(msg.author_id?.[0]);
            }

            this.state.messages = messages;
            this.state.notes = notes;
        } catch (e) {
            console.error("Error loading messages:", e);
            this.state.messages = [];
            this.state.notes = [];
        }
        this.state.isLoadingMessages = false;
    }

    async getInternalPartnerIds(partnerIds) {
        /**
         * Batch query to check which partners are internal users.
         * Returns a Set of partner IDs that have linked users.
         */
        if (!partnerIds.length) return new Set();
        try {
            const users = await this.orm.searchRead(
                "res.users",
                [["partner_id", "in", partnerIds]],
                ["partner_id"],
                {limit: partnerIds.length}
            );
            return new Set(users.map((u) => u.partner_id[0]));
        } catch {
            return new Set();
        }
    }

    // ==================== Event Handlers ====================

    // Sidebar handlers
    onFilterChange(filter, value) {
        if (filter === "team") {
            this.state.teamFilter = value;
        } else if (filter === "channel") {
            this.state.channelFilter =
                this.state.channelFilter === value ? null : value;
        } else if (filter === "label") {
            this.state.labelFilter = value;
        } else {
            this.state.filter = filter;
            this.state.activeFolder = null;
        }
        this.state.selectedConversation = null;
        this.state.messages = [];
        this.state.notes = [];
        this.loadConversations();
    }

    onFolderSelect(folder) {
        this.state.activeFolder = folder;
        this.state.filter = null;
        this.state.selectedConversation = null;
        this.state.messages = [];
        this.state.notes = [];
        this.loadConversations();
    }

    toggleSidebarCollapse() {
        this.state.sidebarCollapsed = !this.state.sidebarCollapsed;
    }

    // Conversation list handlers
    onConversationSelect(conversation) {
        this.state.selectedConversation = conversation;
        this.loadMessages(conversation.id);
        // On mobile, switch to chat view
        if (window.innerWidth < 768) {
            this.state.mobileView = "chat";
        }
    }

    onListFilterChange(filter) {
        this.state.filter = filter;
        this.state.selectedConversation = null;
        this.state.messages = [];
        this.loadConversations();
    }

    // eslint-disable-next-line no-unused-vars
    onSearch(query) {
        // Search is handled client-side in ConversationList component
        // Could add server-side search here for large datasets
    }

    // Chat panel handlers
    async onSendMessage(content, attachments = []) {
        if (!this.state.selectedConversation || !content.trim()) return;

        try {
            const attachmentIds = [];
            // Upload attachments first
            for (const att of attachments) {
                const result = await this.orm.create("ir.attachment", [
                    {
                        name: att.name,
                        datas: att.data,
                        res_model: "engage.conversation",
                        res_id: this.state.selectedConversation.id,
                    },
                ]);
                attachmentIds.push(result[0]);
            }

            await this.orm.call(
                "engage.conversation",
                "message_post",
                [this.state.selectedConversation.id],
                {
                    body: content,
                    message_type: "comment",
                    attachment_ids: attachmentIds,
                }
            );

            await this.loadMessages(this.state.selectedConversation.id);
            await this.loadConversations();
        } catch (e) {
            console.error("Error sending message:", e);
            this.notification.add("Failed to send message", {type: "danger"});
        }
    }

    async onSendNote(content) {
        if (!this.state.selectedConversation || !content.trim()) return;

        try {
            await this.orm.call("engage.conversation", "action_add_note", [
                this.state.selectedConversation.id,
                content,
            ]);
            await this.loadMessages(this.state.selectedConversation.id);
        } catch (e) {
            console.error("Error sending note:", e);
            this.notification.add("Failed to add note", {type: "danger"});
        }
    }

    async onAssign() {
        if (!this.state.selectedConversation) return;

        try {
            await this.orm.call("engage.conversation", "action_assign_to_me", [
                this.state.selectedConversation.id,
            ]);
            this.state.selectedConversation.user_id = [this.userId, this.userName];
            await this.loadConversations();
            await this.loadCounts();
            this.notification.add("Conversation assigned to you", {type: "success"});
        } catch (e) {
            console.error("Error assigning conversation:", e);
            this.notification.add("Failed to assign conversation", {type: "danger"});
        }
    }

    async onStatusChange(stageCode) {
        if (!this.state.selectedConversation) return;

        try {
            const actionMap = {
                open: "action_open",
                pending: "action_pending",
                resolved: "action_resolve",
                closed: "action_close",
            };

            const method = actionMap[stageCode];
            if (method) {
                await this.orm.call("engage.conversation", method, [
                    this.state.selectedConversation.id,
                ]);
                await this.loadConversations();
                await this.loadCounts();
                this.notification.add(`Conversation marked as ${stageCode}`, {
                    type: "success",
                });
            }
        } catch (e) {
            console.error("Error changing status:", e);
            this.notification.add(
                "Failed to change status: " + (e.message || "Invalid transition"),
                {type: "danger"}
            );
        }
    }

    onOpenForm() {
        if (!this.state.selectedConversation) return;
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "engage.conversation",
            res_id: this.state.selectedConversation.id,
            views: [[false, "form"]],
            target: "current",
        });
    }

    async onAddLabel() {
        // This would open a label selection dialog
        // For now, we'll just show a notification
        this.notification.add("Label management coming soon", {type: "info"});
    }

    // Contact panel handlers
    onOpenPartner(partnerId) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "res.partner",
            res_id: partnerId,
            views: [[false, "form"]],
            target: "current",
        });
    }

    toggleContactPanelCollapse() {
        this.state.contactPanelCollapsed = !this.state.contactPanelCollapsed;
    }

    // Mobile navigation
    onMobileBack() {
        this.state.mobileView = "list";
        this.state.selectedConversation = null;
    }

    // ==================== Computed Properties ====================

    get inboxClass() {
        const classes = ["o_engage_inbox", "d-flex"];
        if (this.state.selectedConversation) {
            classes.push("conversation-selected");
        }
        if (this.state.mobileView === "chat") {
            classes.push("mobile-chat-view");
        }
        return classes.join(" ");
    }
}

registry.category("actions").add("engage_inbox", EngageInbox);
