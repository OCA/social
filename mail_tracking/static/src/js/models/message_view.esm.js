/** @odoo-module **/

import {registerPatch} from "@mail/model/model_core";

registerPatch({
    name: "MessageView",
    recordMethods: {
        _onTrackingStatusClick(event) {
            var tracking_email_id = $(event.currentTarget).data("tracking");
            event.preventDefault();
            return this.env.services.action.doAction({
                type: "ir.actions.act_window",
                view_type: "form",
                view_mode: "form",
                res_model: "mail.tracking.email",
                views: [[false, "form"]],
                target: "new",
                res_id: tracking_email_id,
            });
        },
        _onMarkFailedMessageReviewed(event) {
            event.preventDefault();
            var messageID = $(event.currentTarget).data("message-id");
            this._markFailedMessageReviewed(messageID);
            window.location.reload();
        },
        _onRetryFailedMessage(event) {
            event.preventDefault();
            var messageID = $(event.currentTarget).data("message-id");
            this.env.services.action.doAction({
                action: "mail.mail_resend_message_action",
                options: {
                    additional_context: {
                        mail_message_to_resend: messageID,
                    },
                    on_close: () => {
                        window.location.reload();
                    },
                },
            });
        },
        _markFailedMessageReviewed(id) {
            return this.env.services.rpc({
                model: "mail.message",
                method: "set_need_action_done",
                args: [[id]],
            });
        },
    },
});
