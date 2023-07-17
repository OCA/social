/** ********************************************************************************
    Copyright 2020 Creu Blanca
    License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).
 **********************************************************************************/

odoo.define("mail_preview_base.preview", function (require) {
    "use strict";

    const DocumentViewer = require("@mail/js/document_viewer")[Symbol.for("default")];
    var basic_fields = require("web.basic_fields");
    var registry = require("web.field_registry");

    DocumentViewer.include({
        init: function (parent, attachments) {
            this._super.apply(this, arguments);
            var self = this;
            _.forEach(this.attachment, function (attachment) {
                if (
                    attachment.mimetype === "application/pdf" ||
                    attachment.type === "text"
                ) {
                    attachment.source_url = self._getContentUrl(attachment);
                } else {
                    attachment.source_url = self._getImageUrl(attachment);
                }
            });
            this.attachment = this.attachment.concat(
                _.filter(attachments, function (attachment) {
                    return self._checkAttachment(attachment);
                })
            );
        },

        /*
            This function is a hook, it will allow to define new kind of
            records
        */
        _checkAttachment: function () {
            return false;
        },
        _getContentUrl: function (attachment) {
            return (
                "/web/content/" +
                attachment.id +
                "?filename=" +
                window.encodeURIComponent(attachment.name)
            );
        },
        _getImageUrl: function (attachment) {
            return "/web/image/" + attachment.id;
        },
        _hasPreview: function (type, attachment) {
            return (
                type === "image" ||
                type === "video" ||
                attachment.mimetype === "application/pdf"
            );
        },
    });

    var FieldPreviewViewer = DocumentViewer.extend({
        init: function (parent, attachments, activeAttachmentID, model, field) {
            this.fieldModelName = model;
            this.fieldName = field;
            this._super.apply(this, arguments);
            this.modelName = model;
        },
        _onDownload: function (e) {
            e.preventDefault();
            window.location =
                "/web/content/" +
                this.fieldModelName +
                "/" +
                this.activeAttachment.id +
                "/" +
                this.fieldName +
                "/" +
                "datas" +
                "?download=true";
        },
        _getContentUrl: function (attachment) {
            return (
                "/web/content/" +
                this.fieldModelName +
                "/" +
                attachment.id +
                "/" +
                this.fieldName +
                "?filename=" +
                window.encodeURIComponent(attachment.name)
            );
        },
        _getImageUrl: function (attachment) {
            return (
                "/web/image/" +
                this.fieldModelName +
                "/" +
                attachment.id +
                "/" +
                this.fieldName
            );
        },
    });

    var FieldPreviewBinary = basic_fields.FieldBinaryFile.extend({
        events: _.extend({}, basic_fields.FieldBinaryFile.prototype.events, {
            "click .preview_file": "_previewFile",
        }),
        init: function () {
            this._super.apply(this, arguments);
            this.mimetype_value = this.recordData.mimetype;
        },
        _previewFile: function (event) {
            event.stopPropagation();
            event.preventDefault();
            var attachmentViewer = new FieldPreviewViewer(
                this,
                [this.attachment],
                this.res_id,
                this.model,
                this.name
            );
            attachmentViewer.appendTo($("body"));
        },
        _renderReadonly: function () {
            this._super.apply(this, arguments);
            if (this.value) {
                this.attachment = {
                    mimetype: this.mimetype_value,
                    id: this.res_id,
                    fileType: this.mimetype_value,
                    name: this.recordData.name,
                };
                var mimetype = this.mimetype_value;
                var type = mimetype.split("/").shift();
                if (DocumentViewer.prototype._hasPreview(type, this.attachment)) {
                    this.$el.prepend(
                        $("<span/>").addClass("fa fa-search preview_file")
                    );
                }
            }
        },
    });

    registry.add("preview_binary", FieldPreviewBinary);

    return {
        FieldPreviewViewer: FieldPreviewViewer,
        FieldPreviewBinary: FieldPreviewBinary,
        DocumentViewer: DocumentViewer,
    };
});
