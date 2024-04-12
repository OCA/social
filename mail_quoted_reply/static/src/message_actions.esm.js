/* @odoo-module */

import {messageActionsRegistry} from "@mail/core/common/message_actions";

messageActionsRegistry.add("reply", {
    icon: "fa-reply",
    title: "Reply",
    onClick: (component) =>
        component.messageService.messageReply(component.props.message),
    condition: (component) => component.canReply,
});
