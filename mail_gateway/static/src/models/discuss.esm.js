/** @odoo-module **/

import {many} from "@mail/model/model_field";
import {registerPatch} from "@mail/model/model_core";

registerPatch({
    name: "Discuss",
    fields: {
        /**
         * Discuss sidebar category for `gateway` channel threads.
         */
        categoryGateways: many("DiscussSidebarCategory", {
            inverse: "discussAsGateways",
        }),
    },
    recordMethods: {
        async handleAddGatewayAutocompleteSource(req, res, gateway_id) {
            this.discussView.update({addingChannelValue: req.term});
            const threads = await this.messaging.models.Thread.searchGatewaysToOpen({
                limit: 10,
                searchTerm: req.term,
                gateway_id,
            });
            const items = threads.map((thread) => {
                const escapedName = escape(thread.name);
                return {
                    id: thread.id,
                    label: escapedName,
                    value: escapedName,
                    gateway_id: gateway_id,
                };
            });
            res(items);
        },
        async handleAddGatewayAutocompleteSelect(ev, ui, gateway_id) {
            // Necessary in order to prevent AutocompleteSelect event's default
            // behaviour as html tags visible for a split second in text area
            ev.preventDefault();
            const channel = this.messaging.models.Thread.insert({
                id: ui.item.id,
                model: "mail.channel",
                gateway_id: gateway_id,
            });
            await channel.join();
            // Channel must be pinned immediately to be able to open it before
            // the result of join is received on the bus.
            channel.update({isServerPinned: true});
            channel.open();
        },
    },
});
