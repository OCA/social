/** @odoo-module **/
import {FailedMessageReview} from "@mail_tracking/components/failed_message_review/failed_message_review.esm";
import {Message} from "@mail/core/common/message";
import {MessageTracking} from "@mail_tracking/components/message_tracking/message_tracking.esm";
import {patch} from "@web/core/utils/patch";

Message.props.push("isFailedMessage?");

Message.components = {
    ...Message.components,
    FailedMessageReview,
    MessageTracking,
};

patch(Message.prototype, {
    get failed_recipients() {
        const error_states = ["error", "rejected", "spam", "bounced", "soft-bounced"];
        return this.message.partner_trackings.filter((message) => {
            return error_states.includes(message.status);
        });
    },
});
