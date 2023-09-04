/** @odoo-module **/

import {MessageList} from "@mail/components/message_list/message_list";
import {registerMessagingComponent} from "@mail/utils/messaging_component";

export class FailedMessageList extends MessageList {
    _onClickTitle() {
        this.messageListView.toggleMessageFailedBoxVisibility();
    }
}

FailedMessageList.template = "mail_tracking.FailedMessageList";

registerMessagingComponent(FailedMessageList);
