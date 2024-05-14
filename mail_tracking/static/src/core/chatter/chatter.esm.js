/** @odoo-module */
import {Chatter} from "@mail/core/web/chatter";
import {FailedMessage} from "@mail_tracking/components/failed_message/failed_message.esm";
import {FailedMessagesPanel} from "@mail_tracking/components/failed_messages_panel/failed_messages_panel.esm";
import {patch} from "@web/core/utils/patch";

const {useState} = owl;

Chatter.components = {
    ...Chatter.components,
    FailedMessage,
    FailedMessagesPanel,
};

/** @type {import("@mail/core/common/chatter").Chatter} */
const ChatterPatch = {
    setup() {
        super.setup(...arguments);
        this.state = useState({
            ...this.state,
            showFailedMessageList: true,
            isSearchFailedOpen: false,
        });
    },
    get failed_messages() {
        return this.state.thread?.messages.filter((message) => {
            return message.is_failed_message;
        });
    },
    toggleFailedMessageList() {
        this.state.showFailedMessageList = !this.state.showFailedMessageList;
    },
    toggleSearchFailedOpen() {
        this.state.isSearchFailedOpen = !this.state.isSearchFailedOpen;
    },
    closeSearchFailed() {
        this.state.isSearchFailedOpen = false;
    },
};

patch(Chatter.prototype, ChatterPatch);
