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
            } else if (
                this.messageAction.messageActionListOwner ===
                this.messageAction.replyAllMessageAction
            ) {
                this.messageAction.messageActionListOwner.message.messageReply(true);
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
                } else if (
                    this.messageAction.messageActionListOwner ===
                    this.messageAction.replyAllMessageAction
                ) {
                    classNames += " fa fa-lg fa-reply-all";
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
                } else if (
                    this.messageAction.messageActionListOwner ===
                    this.messageAction.replyAllMessageAction
                ) {
                    return this.env._t("Reply All");
                }
                return this._super();
            },
        },
    },
});
