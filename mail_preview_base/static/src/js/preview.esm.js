/** @odoo-module **/

/** ********************************************************************************
    Copyright 2020 Creu Blanca
    License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).
 **********************************************************************************/

import {BinaryField} from "@web/views/fields/binary/binary_field";
import {registry} from "@web/core/registry";
import {useService} from "@web/core/utils/hooks";

export class PreviewBinary extends BinaryField {
    setup() {
        super.setup();
        this.messaging = useService("messaging");
    }
    previewFile() {
        var rec = this.props.record;
        this.openAttachmentPreview(rec);
    }

    async openAttachmentPreview(attachment) {
        this.messaging.get().then((messaging) => {
            const attachmentList = messaging.models.AttachmentList.insert({
                selectedAttachment: messaging.models.Attachment.insert({
                    id: attachment.resId,
                    filename: attachment.data.name,
                    name: attachment.data.name,
                    mimetype: attachment.data.mimetype,
                }),
            });
            this.dialog = messaging.models.Dialog.insert({
                attachmentListOwnerAsAttachmentView: attachmentList,
            });
        });
        return;
    }
}

PreviewBinary.template = "mail_preview_base.BinaryField";

registry.category("fields").add("preview_binary", PreviewBinary);
