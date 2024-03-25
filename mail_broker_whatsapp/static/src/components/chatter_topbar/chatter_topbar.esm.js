/** @odoo-module **/

import {registerPatch} from "@mail/model/model_core";

registerPatch({
    name: "Chatter",
    recordMethods: {
        async onClickSendWhatsapp() {
            if (this.isTemporary) {
                const saved = await this.doSaveRecord();
                if (!saved) {
                    return;
                }
            }
            this.env.services.action.doAction(
                "mail_broker_whatsapp.whatsapp_thread_composer_act_window",
                {
                    additionalContext: {
                        default_res_id: this.thread.id,
                        default_model: this.thread.model,
                        partners: this.thread.followersPartner.map(
                            (partner) => partner.id
                        ),
                    },
                }
            );
        },
    },
});
