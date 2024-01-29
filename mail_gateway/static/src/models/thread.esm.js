/** @odoo-module **/

import {many, one} from "@mail/model/model_field";
import {registerPatch} from "@mail/model/model_core";

registerPatch({
    name: "Thread",
    fields: {
        gateway: one("Gateway"),
        messagesAsGatewayThread: many("Message", {
            inverse: "gatewayThread",
            isCausal: true,
        }),
        hasInviteFeature: {
            compute() {
                if (this.channel && this.channel.channel_type === "gateway") {
                    return true;
                }
                return this._super();
            },
        },
        hasMemberListFeature: {
            compute() {
                if (this.channel && this.channel.channel_type === "gateway") {
                    return true;
                }
                return this._super();
            },
        },
        isChatChannel: {
            compute() {
                if (this.channel && this.channel.channel_type === "gateway") {
                    return true;
                }
                return this._super();
            },
        },
    },
    modelMethods: {
        convertData(data) {
            var data2 = this._super(data);
            if (data.gateway_id) {
                data2.gateway = {id: data.gateway_id};
            }
            return data2;
        },
        async searchGatewaysToOpen({limit, searchTerm, gateway_id}) {
            const domain = [
                ["channel_type", "=", "gateway"],
                ["name", "ilike", searchTerm],
                ["gateway_id", "=", gateway_id],
            ];
            const fields = ["channel_type", "name"];
            const channelsData = await this.messaging.rpc({
                model: "mail.channel",
                method: "search_read",
                kwargs: {
                    domain,
                    fields,
                    limit,
                },
            });
            return this.insert(
                channelsData.map((channelData) =>
                    this.messaging.models.Thread.convertData({
                        channel: {
                            channel_type: channelData.channel_type,
                            id: channelData.id,
                        },
                        id: channelData.id,
                        name: channelData.name,
                    })
                )
            );
        },
    },
});
