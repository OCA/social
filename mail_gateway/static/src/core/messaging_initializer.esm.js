/** @odoo-module **/

import {registerPatch} from "@mail/model/model_core";

registerPatch({
    name: "MessagingInitializer",
    recordMethods: {
        async _init({gateways}) {
            const discuss = this.messaging.discuss;
            if (gateways) {
                this.messaging.executeGracefully(
                    gateways.map((gatewayData) => () => {
                        this.messaging.models.DiscussSidebarCategory.insert({
                            discussAsGateways: discuss,
                            gateway: gatewayData,
                            gateway_id: gatewayData.id,
                        });
                    })
                );
            }
            this._super(...arguments);
        },
    },
});
