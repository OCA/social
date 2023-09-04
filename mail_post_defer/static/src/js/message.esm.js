/** @odoo-module **/
import {registerPatch} from "@mail/model/model_core";

// Ensure that the model definition is loaded before the patch
import "@mail/models/message";

registerPatch({
    name: "Message",

    fields: {
        canBeDeleted: {
            /**
             * Whether this message can be updated.
             *
             * Despite the field name, this method is used upstream to determine
             * whether a message can be edited or deleted.
             *
             * Upstream Odoo allows updating notes. We want to allow updating any
             * user message that is not yet sent. If there's a race condition,
             * anyways the server will repeat these checks.
             *
             * @returns {Boolean}
             *  Whether this message can be updated.
             * @override
             */
            compute() {
                // If upstream allows editing, we are done
                if (this._super()) {
                    return true;
                }
                // Repeat upstream checks that are still valid for us
                if (this.trackingValues.length > 0) {
                    return false;
                }
                if (this.message_type !== "comment") {
                    return false;
                }
                if (this.originThread.model === "mail.channel") {
                    return true;
                }
                // Check that no notification has been sent yet
                if (
                    this.notifications.some((ntf) => ntf.notification_status === "sent")
                ) {
                    return false;
                }
                return true;
            },
        },
    },
});
