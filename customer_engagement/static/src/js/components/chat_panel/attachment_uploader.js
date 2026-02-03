/** @odoo-module **/

import {Component, useRef, useState} from "@odoo/owl";
import {useService} from "@web/core/utils/hooks";

export class AttachmentUploader extends Component {
    static template = "customer_engagement.AttachmentUploader";
    static props = {
        attachments: {type: Array},
        onAdd: {type: Function},
        onRemove: {type: Function},
        maxSize: {type: Number, optional: true}, // In MB
        acceptedTypes: {type: String, optional: true},
    };

    setup() {
        this.notification = useService("notification");
        this.state = useState({
            isUploading: false,
            dragOver: false,
        });
        this.fileInputRef = useRef("fileInput");
    }

    get maxSizeBytes() {
        return (this.props.maxSize || 10) * 1024 * 1024; // Default 10MB
    }

    get acceptTypes() {
        return (
            this.props.acceptedTypes || "image/*,application/pdf,.doc,.docx,.xls,.xlsx"
        );
    }

    onFileInputClick() {
        this.fileInputRef.el.click();
    }

    async onFileChange(ev) {
        const files = ev.target.files;
        await this.processFiles(files);
        ev.target.value = ""; // Reset input
    }

    onDragOver(ev) {
        ev.preventDefault();
        this.state.dragOver = true;
    }

    onDragLeave(ev) {
        ev.preventDefault();
        this.state.dragOver = false;
    }

    async onDrop(ev) {
        ev.preventDefault();
        this.state.dragOver = false;
        const files = ev.dataTransfer.files;
        await this.processFiles(files);
    }

    async processFiles(files) {
        for (const file of files) {
            if (file.size > this.maxSizeBytes) {
                this.notification.add(
                    `File "${file.name}" is too large. Maximum size is ${
                        this.props.maxSize || 10
                    }MB.`,
                    {type: "warning"}
                );
                continue;
            }

            this.state.isUploading = true;

            try {
                const attachment = await this.uploadFile(file);
                this.props.onAdd(attachment);
            } catch (error) {
                this.notification.add(
                    `Failed to upload "${file.name}": ${error.message}`,
                    {type: "danger"}
                );
            }

            this.state.isUploading = false;
        }
    }

    async uploadFile(file) {
        // Create a base64 representation for preview
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = () => {
                resolve({
                    name: file.name,
                    size: file.size,
                    mimetype: file.type,
                    data: reader.result.split(",")[1], // Base64 data
                    url: URL.createObjectURL(file), // For preview
                    file: file, // Keep reference to file
                });
            };
            reader.onerror = () => reject(new Error("Failed to read file"));
            reader.readAsDataURL(file);
        });
    }

    onRemoveClick(attachment) {
        this.props.onRemove(attachment);
    }

    getFileIcon(attachment) {
        const type = attachment.mimetype || "";
        if (type.startsWith("image/")) return "fa-image";
        if (type.startsWith("video/")) return "fa-video-camera";
        if (type.startsWith("audio/")) return "fa-music";
        if (type.includes("pdf")) return "fa-file-pdf-o";
        if (type.includes("word")) return "fa-file-word-o";
        if (type.includes("excel") || type.includes("spreadsheet"))
            return "fa-file-excel-o";
        if (type.includes("zip") || type.includes("rar")) return "fa-file-archive-o";
        return "fa-file-o";
    }

    formatSize(bytes) {
        if (bytes < 1024) return bytes + " B";
        if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
        return (bytes / (1024 * 1024)).toFixed(1) + " MB";
    }

    isImage(attachment) {
        return attachment.mimetype && attachment.mimetype.startsWith("image/");
    }
}
