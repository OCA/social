/** @odoo-module **/

import {Message} from "@mail/components/message/message";
import {patch} from "web.utils";

patch(Message.prototype, "mail_tracking/static/src/js/message.js", {
    constructor() {
        this._super(...arguments);
    },
    _onTrackingStatusClick(event) {
        var tracking_email_id = $(event.currentTarget).data("tracking");
        event.preventDefault();
        return this.env.bus.trigger("do-action", {
            action: {
                type: "ir.actions.act_window",
                view_type: "form",
                view_mode: "form",
                res_model: "mail.tracking.email",
                views: [[false, "form"]],
                target: "new",
                res_id: tracking_email_id,
            },
        });
    },

    //        For discuss
    _onMarkFailedMessageReviewed(event) {
        event.preventDefault();
        var messageID = $(event.currentTarget).data("message-id");
        this._markFailedMessageReviewed(messageID);
        window.location.reload();
    },
    _onRetryFailedMessage(event) {
        event.preventDefault();
        var messageID = $(event.currentTarget).data("message-id");
        this.env.bus.trigger("do-action", {
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
});
