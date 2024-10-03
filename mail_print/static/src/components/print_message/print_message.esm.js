/** @odoo-module **/
/*  Copyright 2024 Tecnativa - Carlos Lopez
    License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
*/
import {registerMessagingComponent} from "@mail/utils/messaging_component";
const {Component} = owl;

export class PrintMessage extends Component {
    onClickPrintMessage() {
        this.env.bus.trigger("do-action", {
            action: "mail_print.mail_message_report",
            options: {
                additional_context: {
                    active_id: this.props.message_id,
                    active_ids: [this.props.message_id],
                    active_model: "mail.message",
                },
            },
        });
    }
}

PrintMessage.template = "mail_print.PrintMessage";
PrintMessage.props = {
    message_id: Number,
};

registerMessagingComponent(PrintMessage);
