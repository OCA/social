/** @odoo-module **/
/*  Copyright 2024 Tecnativa - Carlos Lopez
    License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
*/
import {registerMessagingComponent} from "@mail/utils/messaging_component";
const {Component} = owl;

export class ForwardMessage extends Component {
    async onClickForwardMessage() {
        const composer = this.props.message.originThread.composer;
        const action = await this.env.services.rpc({
            model: "mail.message",
            method: "action_wizard_forward",
            args: [[this.props.message.id]],
        });
        this.env.bus.trigger("do-action", {
            action: action,
            options: {
                additional_context: {
                    active_id: this.props.message.id,
                    active_ids: [this.props.message.id],
                    active_model: "mail.message",
                },
                on_close: () => {
                    if (composer.exists()) {
                        composer._reset();
                        if (composer.activeThread) {
                            composer.activeThread.loadNewMessages();
                            composer.activeThread.refreshFollowers();
                            composer.activeThread.fetchAndUpdateSuggestedRecipients();
                        }
                    }
                },
            },
        });
    }
}

ForwardMessage.template = "mail_forward.ForwardMessage";
ForwardMessage.props = {
    message: Object,
};

registerMessagingComponent(ForwardMessage);
