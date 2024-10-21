import {useService} from "@web/core/utils/hooks";

const {Component, useState} = owl;

export class FailedMessageReview extends Component {
    static props = ["message"];
    static template = "mail_tracking.FailedMessageReview";

    setup() {
        this.message = useState(this.props.message);
        this.orm = useService("orm");
    }
    async setFailedMessageReviewed() {
        await this.orm.call("mail.message", "set_need_action_done", [
            [this.message.id],
        ]);
        // Debugger
        this.thread.fetchNewMessages();
        if (this.props.reloadParentView) {
            this.props.reloadParentView();
        }
    }
    retryFailedMessage() {
        this.env.services.action.doAction("mail.mail_resend_message_action", {
            additionalContext: {
                mail_message_to_resend: this.message.id,
            },
            onClose: async () => {
                // Check if message is still 'failed' after Retry
                await this.orm.call("mail.message", "get_failed_messages", [
                    [this.message.id],
                ]);
            },
        });
    }
    get thread() {
        return this.props.message.thread;
    }
    get failed_recipients() {
        const error_states = ["error", "rejected", "spam", "bounced", "soft-bounced"];
        return this.message.partner_trackings.filter((message) => {
            return error_states.includes(message.status);
        });
    }
}
