/** @odoo-module **/

import {registerPatch} from "@mail/model/model_core";

registerPatch({
    name: "ChannelMemberView",
    recordMethods: {
        onClickMember(ev) {
            if (
                this.channelMember.persona.guest &&
                this.channelMember.persona.guest.gateway
            ) {
                ev.stopPropagation();
                return this.env.services.action.doAction({
                    name: this.env._t("Manage guest"),
                    type: "ir.actions.act_window",
                    res_model: "mail.guest.manage",
                    context: {default_guest_id: this.channelMember.persona.guest.id},
                    views: [[false, "form"]],
                    target: "new",
                });
            }
            return this._super();
        },
    },
    fields: {
        hasOpenChat: {
            compute() {
                return (
                    this._super() ||
                    Boolean(
                        this.channelMember.persona.guest &&
                            this.channelMember.persona.guest.gateway
                    )
                );
            },
        },
    },
});
