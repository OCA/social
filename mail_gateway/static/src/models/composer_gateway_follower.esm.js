/** @odoo-module **/

import {attr, one} from "@mail/model/model_field";
import {registerModel} from "@mail/model/model_core";

registerModel({
    name: "composerGatewayFollower",
    recordMethods: {
        _getMessageData() {
            return {
                partner_id: this.follower.partner.id,
                channel_type: "gateway",
                gateway_channel_id: this.channel,
            };
        },
    },
    fields: {
        component: attr(),
        follower: one("Follower", {identifying: true}),
        composer: one("Composer", {
            identifying: true,
            inverse: "composerGatewayFollowers",
        }),
        channel_type: attr({}),
        channel: attr(),
        hasGatewayChannels: attr({
            compute() {
                return this.follower.partner.gateway_channels.length > 0;
            },
        }),
    },
});
