/* @odoo-module */

import {PrintMessage} from "../../components/print_message/print_message.esm";
import {messageActionsRegistry} from "@mail/core/common/message_actions";

messageActionsRegistry.add("print", {
    callComponent: PrintMessage,
    props: (component) => ({message_id: component.props.message.id}),
    condition: (component) => !component.props.message.is_note,
    sequence: 10,
});
