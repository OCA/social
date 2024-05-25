/** @odoo-module **/

import {attr, many} from "@mail/model/model_field";
import {clear} from "@mail/model/model_field_command";
import {registerPatch} from "@mail/model/model_core";

registerPatch({
    name: "Composer",
    fields: {
        isGateway: attr({
            default: false,
        }),
        composerGatewayFollowers: many("composerGatewayFollower", {
            compute() {
                if (this.thread && this.isGateway) {
                    return this.thread.followers
                        .filter(
                            (follower) => follower.partner.gateway_channels.length > 0
                        )
                        .map((follower) => {
                            return {
                                follower,
                                channel: follower.partner.gateway_channels[0].id,
                            };
                        });
                }
                return clear();
            },
            inverse: "composer",
        }),
    },
});
