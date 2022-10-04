/** @odoo-module **/

import {MessageActionList} from "@mail/components/message_action_list/message_action_list";
import {patch} from "web.utils";
import {qweb} from "web.core";

const {onMounted} = owl.hooks;

patch(
    MessageActionList.prototype,
    "mail_quoted_reply/static/src/components/mail_message_reply.js",
    {
        xmlDependencies: (MessageActionList.prototype.xmlDependencies || []).concat([
            "/mail_quoted_reply/static/src/xml/mail_message_reply.xml",
        ]),

        setup() {
            this._super();
            onMounted(() => {
                var actionLists = document.querySelectorAll(".o_MessageActionList");
                var MessageQuotedReplyIcon = $(
                    qweb.render("MessageQuotedReplyButton", this)
                )[0];
                if (typeof MessageQuotedReplyIcon !== "undefined") {
                    MessageQuotedReplyIcon.addEventListener(
                        "click",
                        this.messaging.models["mail.message_action_list"].get(
                            this.props.messageActionListLocalId
                        ).onClickMailMessageReply
                    );
                }
                actionLists.forEach((actionList) => {
                    actionList.append(MessageQuotedReplyIcon);
                });
            });
        },
    }
);
