/** @odoo-module **/

import {MessageList} from "@mail/components/message_list/message_list";
import {patch} from "web.utils";
import {useStore} from "../../client_actions/failed_message_storage.esm";

patch(MessageList.prototype, "mail_tracking/static/src/js/message_list.esm.js", {
    setup() {
        this._super(...arguments);
        this.store = useStore();
    },
});
