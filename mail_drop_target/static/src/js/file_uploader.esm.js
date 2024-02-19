/** @odoo-module **/

import {registerPatch} from "@mail/model/model_core";

registerPatch({
    name: "FileUploader",
    recordMethods: {
        /**
         * @override
         */
        _onAttachmentUploaded({attachmentData}) {
            if (attachmentData.email_upload) {
                const chatter =
                    this.chatterOwner ||
                    (this.attachmentBoxView && this.attachmentBoxView.chatter) ||
                    (this.activityView && this.activityView.activityBoxView.chatter);
                if (chatter && chatter.exists()) {
                    chatter.reloadParentView();
                }
                return;
            }
            return this._super.apply(this, arguments);
        },
    },
});
