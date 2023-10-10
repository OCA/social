/** @odoo-module **/

import {Message} from "@mail/components/message/message";
import {patch} from "web.utils";
import {useStore} from "../../client_actions/failed_message_storage.esm";

patch(Message.prototype, "mail_tracking/static/src/components/message/message.esm.js", {
    constructor() {
        this._super(...arguments);
    },
    setup() {
        this._super(...arguments);
        this.store = useStore();
    },
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
    _addMessageIdToStore(messageID) {
        this.store.addMessage(messageID);
    },
    async _onMarkFailedMessageReviewed(event) {
        event.preventDefault();
        const messageID = $(event.currentTarget).data("message-id");
        const messageNeedsAction = await this._markFailedMessageReviewed(messageID);
        // Add the reviewed message ID to storage so it is excluded from the list of rendered messages
        if (!messageNeedsAction) {
            this._addMessageIdToStore(messageID);
        }
    },
    _onRetryFailedMessage(event) {
        event.preventDefault();
        const messageID = $(event.currentTarget).data("message-id");
        this.env.services.action.doAction("mail.mail_resend_message_action", {
            additionalContext: {
                mail_message_to_resend: messageID,
            },
            onClose: async () => {
                // Check if message is still 'failed' after Retry, and if it is not, add its ID to storage so
                // it is excluded from the list of rendered messages
                const failedMessages = await this.messaging.rpc({
                    model: "mail.message",
                    method: "get_failed_messages",
                    args: [[messageID]],
                });
                const failedMessageIds = failedMessages.map((message) => {
                    return (message || {}).id;
                });
                if (failedMessageIds.length && !failedMessageIds.includes(messageID))
                    this._addMessageIdToStore(messageID);
            },
        });
    },
    _markFailedMessageReviewed(id) {
        return this.messaging.rpc({
            model: "mail.message",
            method: "set_need_action_done",
            args: [[id]],
        });
    },
});
