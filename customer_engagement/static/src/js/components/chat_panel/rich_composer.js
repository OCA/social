/** @odoo-module **/

import {Component, onMounted, useRef, useState} from "@odoo/owl";
import {useService} from "@web/core/utils/hooks";
import {EmojiPicker} from "./emoji_picker";
import {CannedResponsePicker} from "./canned_response_picker";
import {AttachmentUploader} from "./attachment_uploader";

export class RichComposer extends Component {
    static template = "customer_engagement.RichComposer";
    static components = {EmojiPicker, CannedResponsePicker, AttachmentUploader};
    static props = {
        mode: {type: String}, // "message" or "note"
        conversationId: {type: Number, optional: true},
        channelType: {type: String, optional: true},
        onSend: {type: Function},
        onModeChange: {type: Function},
        showEmojiPicker: {type: Boolean},
        showCannedPicker: {type: Boolean},
        onToggleEmoji: {type: Function},
        onToggleCanned: {type: Function},
        onClosePickers: {type: Function},
    };

    setup() {
        this.orm = useService("orm");
        this.state = useState({
            content: "",
            attachments: [],
            cannedSuggestions: [],
            isUploading: false,
        });
        this.textareaRef = useRef("textarea");

        onMounted(() => {
            this.focusTextarea();
        });
    }

    focusTextarea() {
        if (this.textareaRef.el) {
            this.textareaRef.el.focus();
        }
    }

    get isNote() {
        return this.props.mode === "note";
    }

    get placeholder() {
        return this.isNote
            ? "Add a private note... (visible only to your team)"
            : "Type a message... (use / for quick replies)";
    }

    get sendButtonClass() {
        return this.isNote ? "btn-warning" : "btn-primary";
    }

    get canSend() {
        return (
            this.state.content.trim().length > 0 || this.state.attachments.length > 0
        );
    }

    onInput(ev) {
        this.state.content = ev.target.value;

        // Check for canned response trigger
        if (this.state.content.startsWith("/")) {
            this.searchCannedResponses(this.state.content.slice(1));
        } else {
            this.state.cannedSuggestions = [];
            this.props.onClosePickers();
        }
    }

    onKeyDown(ev) {
        // Send on Enter (without Shift)
        if (ev.key === "Enter" && !ev.shiftKey) {
            ev.preventDefault();
            this.send();
        }
        // Escape to close pickers
        if (ev.key === "Escape") {
            this.props.onClosePickers();
        }
    }

    async searchCannedResponses(query) {
        if (query.length < 1) {
            this.state.cannedSuggestions = [];
            return;
        }

        const responses = await this.orm.searchRead(
            "engage.canned.response",
            [
                ["shortcut", "ilike", query],
                ["active", "=", true],
            ],
            ["shortcut", "name", "content", "plain_content"],
            {limit: 5, order: "usage_count desc, sequence"}
        );

        this.state.cannedSuggestions = responses;
        if (responses.length > 0) {
            // Show inline suggestions instead of picker
        }
    }

    onCannedSelect(response) {
        // Replace the /shortcut with the response content
        // Strip HTML for plain text channels
        let content = response.plain_content || response.content;

        // Remove HTML tags for non-email channels
        if (this.props.channelType !== "email") {
            const temp = document.createElement("div");
            temp.innerHTML = content;
            content = temp.textContent || temp.innerText || "";
        }

        this.state.content = content;
        this.state.cannedSuggestions = [];
        this.props.onClosePickers();

        // Increment usage count
        this.orm.call("engage.canned.response", "increment_usage", [[response.id]]);

        this.focusTextarea();
    }

    onEmojiSelect(emoji) {
        const textarea = this.textareaRef.el;
        const start = textarea.selectionStart;
        const end = textarea.selectionEnd;
        const before = this.state.content.substring(0, start);
        const after = this.state.content.substring(end);

        this.state.content = before + emoji + after;
        this.props.onClosePickers();

        // Set cursor position after emoji
        setTimeout(() => {
            textarea.selectionStart = textarea.selectionEnd = start + emoji.length;
            textarea.focus();
        }, 0);
    }

    onAttachmentAdd(attachment) {
        this.state.attachments.push(attachment);
    }

    onAttachmentRemove(attachment) {
        const index = this.state.attachments.indexOf(attachment);
        if (index > -1) {
            this.state.attachments.splice(index, 1);
        }
    }

    setMode(mode) {
        this.props.onModeChange(mode);
    }

    async send() {
        if (!this.canSend) return;

        await this.props.onSend(this.state.content, this.state.attachments);
        this.state.content = "";
        this.state.attachments = [];
        this.focusTextarea();
    }
}
