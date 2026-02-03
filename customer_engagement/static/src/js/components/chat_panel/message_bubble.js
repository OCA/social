/** @odoo-module **/

import {Component} from "@odoo/owl";

export class MessageBubble extends Component {
    static template = "customer_engagement.MessageBubble";
    static props = {
        message: {type: Object},
        isOutgoing: {type: Boolean},
    };

    get authorName() {
        const msg = this.props.message;
        if (msg.author_id && msg.author_id[1]) {
            return msg.author_id[1];
        }
        return "Unknown";
    }

    get authorInitials() {
        return this.authorName
            .split(" ")
            .map((word) => word[0])
            .slice(0, 2)
            .join("")
            .toUpperCase();
    }

    get formattedTime() {
        const date = new Date(this.props.message.date);
        return date.toLocaleTimeString(undefined, {
            hour: "2-digit",
            minute: "2-digit",
        });
    }

    get bubbleClass() {
        const classes = ["o_message_bubble"];
        if (this.props.isOutgoing) {
            classes.push("outgoing");
        } else {
            classes.push("incoming");
        }
        return classes.join(" ");
    }

    get hasAttachments() {
        return (
            this.props.message.attachment_ids &&
            this.props.message.attachment_ids.length > 0
        );
    }

    get attachments() {
        return this.props.message.attachment_ids || [];
    }

    /**
     * Get delivery status for outgoing messages
     * Returns: pending, sent, delivered, read, failed
     */
    get deliveryStatus() {
        if (!this.props.isOutgoing) {
            return null;
        }
        return this.props.message.delivery_status || "sent";
    }

    /**
     * Get delivery status icon class
     */
    get deliveryStatusIcon() {
        const status = this.deliveryStatus;
        switch (status) {
            case "pending":
                return "fa-clock-o"; // Clock for pending
            case "sent":
                return "fa-check"; // Single check for sent
            case "delivered":
                return "fa-check-double"; // Double check for delivered (using custom or fallback)
            case "read":
                return "fa-check-double text-info"; // Blue double check for read
            case "failed":
                return "fa-exclamation-circle text-danger"; // Error icon for failed
            default:
                return "fa-check";
        }
    }

    /**
     * Check if we should show double check (delivered or read)
     */
    get isDoubleCheck() {
        return ["delivered", "read"].includes(this.deliveryStatus);
    }

    /**
     * Check if message was read
     */
    get isRead() {
        return this.deliveryStatus === "read";
    }

    /**
     * Get delivery status tooltip text
     */
    get deliveryStatusTitle() {
        const status = this.deliveryStatus;
        const titles = {
            pending: "Sending...",
            sent: "Sent",
            delivered: "Delivered",
            read: "Read",
            failed: "Failed to send",
        };
        return titles[status] || "Sent";
    }

    /**
     * Check if message has a reply-to reference
     */
    get hasReplyTo() {
        return Boolean(this.props.message.reply_to_message_id);
    }

    /**
     * Get reply-to message preview
     */
    get replyToPreview() {
        const replyTo = this.props.message.reply_to_message_id;
        if (!replyTo) return null;
        // If it's an array [id, name], extract the preview
        if (Array.isArray(replyTo) && replyTo[1]) {
            return replyTo[1].substring(0, 50) + (replyTo[1].length > 50 ? "..." : "");
        }
        return null;
    }

    getAttachmentIcon(attachment) {
        const mimetype = attachment.mimetype || "";
        if (mimetype.startsWith("image/")) return "fa-image";
        if (mimetype.startsWith("video/")) return "fa-video-camera";
        if (mimetype.startsWith("audio/")) return "fa-music";
        if (mimetype.includes("pdf")) return "fa-file-pdf-o";
        if (mimetype.includes("word")) return "fa-file-word-o";
        if (mimetype.includes("excel") || mimetype.includes("spreadsheet"))
            return "fa-file-excel-o";
        return "fa-file-o";
    }

    isImageAttachment(attachment) {
        const mimetype = attachment.mimetype || "";
        return mimetype.startsWith("image/");
    }
}
