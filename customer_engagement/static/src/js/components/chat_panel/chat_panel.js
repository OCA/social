/** @odoo-module **/

import {Component, onWillUpdateProps, useRef, useState} from "@odoo/owl";
import {ChatHeader} from "./chat_header";
import {MessageList} from "./message_list";
import {RichComposer} from "./rich_composer";

export class ChatPanel extends Component {
    static template = "customer_engagement.ChatPanel";
    static components = {ChatHeader, MessageList, RichComposer};
    static props = {
        conversation: {type: Object, optional: true},
        messages: {type: Array},
        notes: {type: Array, optional: true},
        isLoading: {type: Boolean},
        currentUserId: {type: Number},
        onSendMessage: {type: Function},
        onSendNote: {type: Function},
        onAssign: {type: Function},
        onStatusChange: {type: Function},
        onOpenForm: {type: Function},
        onAddLabel: {type: Function, optional: true},
        onRemoveLabel: {type: Function, optional: true},
    };

    setup() {
        this.state = useState({
            composerMode: "message", // "message" or "note"
            showEmojiPicker: false,
            showCannedPicker: false,
        });
        this.messageListRef = useRef("messageList");

        onWillUpdateProps((nextProps) => {
            // Scroll to bottom when messages change
            if (nextProps.messages !== this.props.messages) {
                this.scrollToBottom();
            }
        });
    }

    scrollToBottom() {
        setTimeout(() => {
            const el = this.messageListRef.el;
            if (el) {
                el.scrollTop = el.scrollHeight;
            }
        }, 100);
    }

    get hasConversation() {
        return this.props.conversation && this.props.conversation.id;
    }

    get isAssignedToMe() {
        if (!this.props.conversation) return false;
        const userId = this.props.conversation.user_id;
        return userId && userId[0] === this.props.currentUserId;
    }

    get isUnassigned() {
        if (!this.props.conversation) return false;
        return !this.props.conversation.user_id;
    }

    get combinedTimeline() {
        // Combine messages and notes into a single timeline
        const timeline = [];

        for (const msg of this.props.messages) {
            timeline.push({
                type: "message",
                date: msg.date,
                data: msg,
            });
        }

        if (this.props.notes) {
            for (const note of this.props.notes) {
                timeline.push({
                    type: "note",
                    date: note.create_date,
                    data: note,
                });
            }
        }

        // Sort by date
        timeline.sort((a, b) => new Date(a.date) - new Date(b.date));
        return timeline;
    }

    setComposerMode(mode) {
        this.state.composerMode = mode;
    }

    async onSend(content, attachments) {
        if (this.state.composerMode === "note") {
            await this.props.onSendNote(content);
        } else {
            await this.props.onSendMessage(content, attachments);
        }
        this.scrollToBottom();
    }

    toggleEmojiPicker() {
        this.state.showEmojiPicker = !this.state.showEmojiPicker;
        this.state.showCannedPicker = false;
    }

    toggleCannedPicker() {
        this.state.showCannedPicker = !this.state.showCannedPicker;
        this.state.showEmojiPicker = false;
    }

    closePickers() {
        this.state.showEmojiPicker = false;
        this.state.showCannedPicker = false;
    }
}
