/* @odoo-module */

import {_t} from "@web/core/l10n/translation";
import {messageActionsRegistry} from "@mail/core/common/message_actions";

// Add "Mark as Unread" action for messages in History mailbox and Search results
messageActionsRegistry.add("mark-as-unread-history", {
    condition: (component) => {
        const message = component.props.message;
        if (!message?.persistent || !component.store.user) {
            return false;
        }
        if (message.isHistory) {
            return true;
        }
        if (component.env.messageCard && !message.isNeedaction) {
            return true;
        }
        return false;
    },
    icon: "fa-eye-slash",
    title: _t("Mark as Unread"),
    onClick: async (component) => {
        const message = component.props.message;
        await component.messageService.setUndone(message);
        // Remove from search results if in search mode
        const messageSearch = component.props.messageSearch;
        if (messageSearch?.messages) {
            const index = messageSearch.messages.findIndex((m) => m.id === message.id);
            if (index !== -1) {
                messageSearch.messages.splice(index, 1);
                messageSearch.count = Math.max(0, messageSearch.count - 1);
            }
        }
    },
    sequence: 15,
});
