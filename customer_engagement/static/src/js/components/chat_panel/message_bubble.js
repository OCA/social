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
