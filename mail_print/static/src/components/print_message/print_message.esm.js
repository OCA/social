/** @odoo-module **/
/*  Copyright 2024 Tecnativa - Carlos Lopez
    License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
*/
const {Component} = owl;

export class PrintMessage extends Component {
    onClickPrintMessage() {
        this.env.services.action.doAction("mail_print.mail_message_report", {
            additionalContext: {
                active_id: this.props.message_id,
                active_ids: [this.props.message_id],
                active_model: "mail.message",
            },
        });
    }
}

PrintMessage.template = "mail_print.PrintMessage";
PrintMessage.props = {
    message_id: Number,
};
