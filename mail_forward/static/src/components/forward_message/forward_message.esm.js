/** @odoo-module **/
/*  Copyright 2024 Tecnativa - Carlos Lopez
    License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
*/
const {Component} = owl;
import {useService} from "@web/core/utils/hooks";

export class ForwardMessage extends Component {
    setup() {
        super.setup();
        this.threadService = useService("mail.thread");
    }
    async onClickForwardMessage() {
        const composer = this.props.message.originThread.composer;
        const action = await this.env.services.orm.call(
            "mail.message",
            "action_wizard_forward",
            [[this.props.message.id]]
        );
        this.env.services.action.doAction(action, {
            additionalContext: {
                active_id: this.props.message.id,
                active_ids: [this.props.message.id],
                active_model: "mail.message",
            },
            onClose: () => {
                if (composer.thread) {
                    this.threadService.fetchNewMessages(composer.thread);
                }
            },
        });
    }
}

ForwardMessage.template = "mail_forward.ForwardMessage";
ForwardMessage.props = {
    message: Object,
};
