/* @odoo-module */

import {_t} from "@web/core/l10n/translation";
import {messageActionsRegistry} from "@mail/core/common/message_actions";

// Add "Mark as Unread" action for messages in History mailbox
messageActionsRegistry.add("mark-as-unread-history", {
    condition: (component) => {
        return (
            component.props.message?.isHistory &&
            component.store.user &&
            component.props.message.persistent
        );
    },
    icon: "fa-eye-slash",
    title: _t("Mark as Unread"),
    onClick: (component) => {
        component.messageService.setUndone(component.props.message);
    },
    sequence: 15,
});
