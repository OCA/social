/** ********************************************************************************
    Copyright 2020 Creu Blanca
    License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).
 **********************************************************************************/

odoo.define("mail_preview_base.preview", function (require) {
    "use strict";

    var DocumentViewer = require("mail.DocumentViewer");
    var basic_fields = require("web.basic_fields");
    var registry = require("web.field_registry");
    var AttachmentBox = require("mail.AttachmentBox");

    DocumentViewer.include({
        init: function (parent, attachments) {
            this._super.apply(this, arguments);
            var self = this;
            _.forEach(this.attachment, function (attachment) {
                if (attachment.mimetype === 'application/pdf' ||
                    attachment.type === 'text'
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
            return "/web/content/" + attachment.id +"?filename=" +
                window.encodeURIComponent(attachment.name);
        },
        _getImageUrl: function (attachment) {
            return "/web/image/" + attachment.id;
        },
        _hasPreview: function (type, attachment) {
            return type === 'image' ||
            type === 'video' ||
            attachment.mimetype === 'application/pdf';
        },
    });

    AttachmentBox.include({
        init: function (parent, record, attachments) {
            _.each(attachments, function (attachment) {
                attachment.has_preview = DocumentViewer.prototype._hasPreview(
                    attachment.mimetype && attachment.mimetype.split('/').shift(),
                    attachment);
            });
            this._super.apply(this, arguments);
        },
    });

    var FieldPreviewViewer = DocumentViewer.extend({
        init: function (parent, attachments, activeAttachmentID, model, field) {
            this.modelName = model;
            this.fieldName = field;
            this._super.apply(this, arguments);
        },
        _onDownload: function (e) {
            e.preventDefault();
            window.location =
                "/web/content/" +
                this.modelName +
                "/" +
                this.activeAttachment.id +
                "/" +
                this.fieldName +
                "/" +
                "datas" +
                "?download=true";
        },
        _getContentUrl: function (attachment) {
            return "/web/content/" +
                this.modelName + '/' +
                attachment.id + '/' +
                this.fieldName +
                "?filename=" +
                window.encodeURIComponent(attachment.name);
        },
        _getImageUrl: function (attachment) {
            return "/web/image/" +
                this.modelName + '/' +
                attachment.id + '/' +
                this.fieldName;
        },
    });

    var FieldPreviewBinary = basic_fields.FieldBinaryFile.extend({
        events: _.extend({}, basic_fields.FieldBinaryFile.prototype.events, {
            "click .preview_file": "_previewFile",
        }),
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
                    mimetype: this.recordData.res_mimetype,
                    id: this.res_id,
                    fileType: this.recordData.res_mimetype,
                    name: this.filename,
                };
                var mimetype = this.recordData.res_mimetype;
                var type = mimetype.split("/").shift();
                if (
                    DocumentViewer.prototype._hasPreview(type, this.attachment)
                ) {
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
