/** @odoo-module */
import {Messaging} from "@mail/core/common/messaging_service";
import {patch} from "@web/core/utils/patch";
import {_t} from "@web/core/l10n/translation";

/** @type {import("@mail/core/common/messaging_service").Messaging} */
const MessagingPatch = {
    setup() {
        super.setup(...arguments);
        this.store.discuss.failed = {
            id: "failed",
            model: "mail.box",
            name: _t("Failed"),
            type: "mailbox",
            counter: 0,
        };
    },
    initMessagingCallback(data) {
        super.initMessagingCallback(data);
        this.store.discuss.failed.counter = data.failed_counter;
    },
};

patch(Messaging.prototype, MessagingPatch);
