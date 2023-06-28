/** @odoo-module **/

import {registerPatch} from "@mail/model/model_core";

registerPatch({
    name: "MessageActionView",
    recordMethods: {
        onClick(ev) {
            if (
                this.messageAction.messageActionListOwner ===
                this.messageAction.replyMessageAction
            ) {
                this.messageAction.messageActionListOwner.message.messageReply();
            } else {
                this._super(ev);
            }
        },
    },
    fields: {
        classNames: {
            compute() {
                let classNames = this._super() || "";
                if (
                    this.messageAction.messageActionListOwner ===
                    this.messageAction.replyMessageAction
                ) {
                    classNames += " fa fa-lg fa-reply";
                }
                return classNames;
            },
        },
        title: {
            compute() {
                if (
                    this.messageAction.messageActionListOwner ===
                    this.messageAction.replyMessageAction
                ) {
                    return this.env._t("Reply");
                }
                return this._super();
            },
        },
    },
});
