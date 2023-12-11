/** @odoo-module **/

import {MessageActionList} from "@mail/components/message_action_list/message_action_list";
import {registerPatch} from "@mail/model/model_core";
import {one} from '@mail/model/model_field';
import {clear} from '@mail/model/model_field_command';
import {markEventHandled} from "@mail/utils/utils";

registerPatch({
    name: 'MessageAction',
    fields: {
        messageActionListOwnerAsQuotedReply: one('MessageActionList', {
            identifying: true,
            inverse: 'actionQuotedReply',
        }),
        messageActionListOwner: {
            compute() {
                if (this.messageActionListOwnerAsQuotedReply) {
                    return this.messageActionListOwnerAsQuotedReply;
                }
                return this._super();
            }
        },
        sequence: {
            compute() {
                if (this.messageActionListOwner === this.messageActionListOwnerAsQuotedReply) {
                    return 7;
                }
                return this._super();
            }
        },
    }
})

registerPatch({
    name: 'MessageActionView',
    recordMethods: {
        onClick(ev) {
            this._super()
            if (this.messageAction.messageActionListOwner
                === this.messageAction.messageActionListOwnerAsQuotedReply) {
                markEventHandled(ev, 'MessageActionList.quotedReply');
                this.messageAction.messageActionListOwner.messageView.quotedReply();
            }
        },
    },
    fields: {
        classNames: {
            compute() {
                if (this.messageAction.messageActionListOwner
                    === this.messageAction.messageActionListOwnerAsQuotedReply) {
                    const classNames = [];
                    classNames.push(this.paddingClassNames);
                    classNames.push("fa fa-lg fa-reply o_MessageActionView_actionQuotedReply")
                    return classNames.join(' ');
                }
                return this._super();
            }
        },
        title: {
            compute() {
                if (this.messageAction.messageActionListOwner
                    === this.messageAction.messageActionListOwnerAsQuotedReply) {
                    return this.env._t("Quoted Reply");
                }
                return this._super()
            }
        },
    },
})

registerPatch({
    name: 'MessageView',
    recordMethods: {
        async quotedReply() {
            const msg_id = this.message.id;
            let action = await this.messaging.rpc({
                model: "mail.message",
                method: "reply_message",
                args: [msg_id],
            });
            if (!action) {
                return;
            }
            await new Promise(resolve => {
                this.env.services.action.doAction(
                    action,
                    {onClose: resolve,},
                );
            });
        }
    }
});

registerPatch({
    name: 'MessageActionList',
    fields: {
        actionQuotedReply: one('MessageAction', {
            compute() {
                if (this.message && !this.message.isTemporary && !this.message.isTransient && !this.message.is_note) {
                    return {}
                }
                return clear();
            },
            inverse: 'messageActionListOwnerAsQuotedReply',
        })
    },
});
