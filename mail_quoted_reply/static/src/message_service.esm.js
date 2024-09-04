/* @odoo-module */

import {patch} from "@web/core/utils/patch";
import {MessageService} from "@mail/core/common/message_service";
import {useService} from "@web/core/utils/hooks";

patch(MessageService.prototype, {
    setup() {
        super.setup();
        this.threadService = useService("mail.thread");
    },

    async messageReply(message) {
        var self = this;
        const thread = message.originThread;
        await this.orm
            .call("mail.message", "reply_message", [message.id])
            .then(function (result) {
                return self.env.services.action.doAction(result, {
                    onClose: async () => {
                        await self.env.services["mail.thread"].fetchData(thread, [
                            "messages",
                        ]);
                        self.env.bus.trigger("update-messages");
                    },
                });
            });
    },
});
