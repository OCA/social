import {_t} from "@web/core/l10n/translation";
import {registerMessageAction} from "@mail/core/common/message_actions";

// Add "Mark as Unread" action for messages in History mailbox and Search results
registerMessageAction("mark-as-unread-history", {
    condition: ({message, owner, store, thread}) => {
        if (!message?.persistent || !store.self) {
            return false;
        }
        if (thread?.eq(store.history)) {
            return true;
        }
        if (owner.env.messageCard && !message.needaction) {
            return true;
        }
        return false;
    },
    icon: "fa fa-eye-slash",
    name: _t("Mark as Unread"),
    onSelected: async ({message, owner}) => {
        await message.setUndone();
        // Remove from search results if in search mode
        const messageSearch = owner.props.messageSearch;
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
