/** @odoo-module **/

import {attr, many} from "@mail/model/model_field";
import {registerPatch} from "@mail/model/model_core";

registerPatch({
    name: "Thread",
    fields: {
        broker_id: attr(),
        messagesAsBrokerThread: many("Message", {
            inverse: "brokerThread",
            isCausal: true,
        }),
        hasInviteFeature: {
            compute() {
                if (this.channel && this.channel.channel_type === "broker") {
                    return true;
                }
                return this._super();
            },
        },
        hasMemberListFeature: {
            compute() {
                if (this.channel && this.channel.channel_type === "broker") {
                    return true;
                }
                return this._super();
            },
        },
        isChatChannel: {
            compute() {
                if (this.channel && this.channel.channel_type === "broker") {
                    return true;
                }
                return this._super();
            },
        },
    },
    modelMethods: {
        convertData(data) {
            var data2 = this._super(data);
            data2.broker_id = data.broker_id;
            return data2;
        },
        async searchBrokersToOpen({limit, searchTerm, broker_id}) {
            const domain = [
                ["channel_type", "=", "broker"],
                ["name", "ilike", searchTerm],
                ["broker_id", "=", broker_id],
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
