/** @odoo-module **/

import {registerPatch} from "@mail/model/model_core";

import rpc from "web.rpc";

registerPatch({
    name: "Message",

    recordMethods: {
        messageReply() {
            var self = this,
                msg_id = this.id;
            rpc.query({
                model: "mail.message",
                method: "reply_message",
                args: [msg_id],
            }).then(function (result) {
                return self.env.services.action.doAction(
                    result,

                    {
                        onClose: async () => {
                            self.originThread.fetchData(["messages"]);
                            self.env.bus.trigger("update-messages");
                        },
                    }
                );
            });
        },
    },
});
