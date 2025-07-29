/* @odoo-module */
import {Chatter} from "@mail/core/web/chatter";
import {patch} from "@web/core/utils/patch";
import {useAttachmentUploader} from "@mail/core/common/attachment_uploader_hook";
import {AttachmentUploadService} from "@mail/core/common/attachment_upload_service";

patch(AttachmentUploadService.prototype, {
    async uploadFile(hooker, file, options) {
        return super.uploadFile(hooker, file, options).then((result) => {
            if (result?.email_upload === 1) {
                hooker.onFileUploaded?.("email_upload");
            }
            return result;
        });
    },
});

patch(Chatter.prototype, {
    setup() {
        super.setup();
        this.attachmentUploader = useAttachmentUploader(this.thread, {
            onFileUploaded: (file) => {
                if (file === "email_upload") {
                    this.reloadParentView?.();
                }
            },
        });
    },
});
