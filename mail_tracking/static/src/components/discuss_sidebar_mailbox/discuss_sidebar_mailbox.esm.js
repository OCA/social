/** @odoo-module **/

import {DiscussSidebarMailbox} from "@mail/components/discuss_sidebar_mailbox/discuss_sidebar_mailbox";
import {patch} from "web.utils";
import {useStore} from "../../client_actions/failed_message_storage.esm";

patch(
    DiscussSidebarMailbox.prototype,
    "mail_tracking/static/src/components/discuss_sidebar_mailbox/discuss_sidebar_mailbox.esm.js",
    {
        setup() {
            this._super(...arguments);
            this.store = useStore();
        },
    }
);
