/** @odoo-module **/

import {registerInstancePatchModel} from "@mail/model/model_core";
import rpc from "web.rpc";

registerInstancePatchModel(
    "mail.message_action_list",
    "mail_quoted_reply/static/src/models/mail_message_reply.js",
    {
        _created() {
            this._super();
            this.onClickMailMessageReply = this.onClickMailMessageReply.bind(this);
        },

        /**
         * @private
         * @param {MouseEvent} ev
         */
        onClickMailMessageReply() {
            var self = this,
                msg_id = this.message.id;
            rpc.query({
                model: "mail.message",
                method: "reply_message",
                args: [msg_id],
            }).then(function (result) {
                self.env.bus.trigger("do-action", {
                    action: result,
                    options: {
                        on_close: () => {
                            self.message.originThread.refresh();
                        },
                    },
                });
            });
        },
    }
);
