/** @odoo-module **/
import {registerPatch} from "@mail/model/model_core";

registerPatch({
    name: "MessageActionView",
    recordMethods: {
        onClick(ev) {
            if (
                this.messageAction.messageActionListOwner ===
                this.messageAction.messageActionListOwnerAsSendGateway
            ) {
                ev.stopPropagation();
                this.env.services.action.doAction({
                    name: this.env._t("Send with gateway"),
                    type: "ir.actions.act_window",
                    res_model: "mail.message.gateway.send",
                    context: {
                        ...this.messageAction.messageActionListOwner.message
                            .gateway_channel_data,
                        default_message_id:
                            this.messageAction.messageActionListOwner.message.id,
                    },
                    views: [[false, "form"]],
                    target: "new",
                });
                return;
            }
            if (
                this.messageAction.messageActionListOwner ===
                this.messageAction.messageActionListOwnerAsAddToThread
            ) {
                ev.stopPropagation();
                this.env.services.action.doAction({
                    name: this.env._t("Link Message to thread"),
                    type: "ir.actions.act_window",
                    res_model: "mail.message.gateway.link",
                    context: {
                        default_message_id:
                            this.messageAction.messageActionListOwner.message.id,
                    },
                    views: [[false, "form"]],
                    target: "new",
                });
                return;
            }
            return this._super(...arguments);
        },
    },
    fields: {
        title: {
            compute() {
                if (
                    this.messageAction.messageActionListOwner ===
                    this.messageAction.messageActionListOwnerAsSendGateway
                ) {
                    return this.env._t("Send with gateway");
                }
                if (
                    this.messageAction.messageActionListOwner ===
                    this.messageAction.messageActionListOwnerAsAddToThread
                ) {
                    return this.env._t("Link to thread");
                }
                return this._super();
            },
        },
        classNames: {
            compute() {
                if (
                    this.messageAction.messageActionListOwner ===
                    this.messageAction.messageActionListOwnerAsSendGateway
                ) {
                    return (
                        this.paddingClassNames +
                        " fa fa-lg fa-share-square-o o_MessageActionView_actionSendGateway"
                    );
                }
                if (
                    this.messageAction.messageActionListOwner ===
                    this.messageAction.messageActionListOwnerAsAddToThread
                ) {
                    return (
                        this.paddingClassNames +
                        " fa fa-lg fa-link o_MessageActionView_actionAddToThread"
                    );
                }
                return this._super();
            },
        },
    },
});
