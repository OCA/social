/** @odoo-module **/

import {registerMessagingComponent} from "@mail/utils/messaging_component";
const {Component} = owl;

export class MessageFailedBox extends Component {
    _onClickTitle() {
        this.chatter.toggleMessageFailedBoxVisibility();
    }
    _markFailedMessageReviewed(id) {
        return this.env.services.rpc({
            model: "mail.message",
            method: "set_need_action_done",
            args: [[id]],
        });
    }
    _onRetryFailedMessage(event) {
        event.preventDefault();
        var messageID = $(event.currentTarget).data("message-id");
        const thread = this.chatter.thread;
        var self = this;
        this.env.bus.trigger("do-action", {
            action: "mail.mail_resend_message_action",
            options: {
                additional_context: {
                    mail_message_to_resend: messageID,
                },
                on_close: () => {
                    self.trigger("reload", {keepChanges: true});
                    thread.refresh();
                },
            },
        });
    }
    _onMarkFailedMessageReviewed(event) {
        event.preventDefault();
        var messageID = $(event.currentTarget).data("message-id");
        this._markFailedMessageReviewed(messageID);
        this.trigger("reload", {keepChanges: true});
        this.chatter.thread.refreshMessagefailed();
        this.chatter.thread.refresh();
    }
}

Object.assign(MessageFailedBox, {
    props: {
        chatterLocalId: String,
    },
    template: "mail_tracking.MessageFailedBox",
});

registerMessagingComponent(MessageFailedBox);
