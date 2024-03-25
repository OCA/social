/** @odoo-module **/

import {registerPatch} from "@mail/model/model_core";

registerPatch({
    name: "MessagingInitializer",
    recordMethods: {
        async _init({brokers}) {
            const discuss = this.messaging.discuss;
            this.messaging.executeGracefully(
                brokers.map((brokerData) => () => {
                    this.messaging.models.DiscussSidebarCategory.insert({
                        discussAsBrokers: discuss,
                        ...brokerData,
                    });
                })
            );
            this._super(...arguments);
        },
    },
});
