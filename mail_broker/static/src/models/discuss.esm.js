/** @odoo-module **/

import {many} from "@mail/model/model_field";
import {registerPatch} from "@mail/model/model_core";

registerPatch({
    name: "Discuss",
    fields: {
        /**
         * Discuss sidebar category for `broker` channel threads.
         */
        categoryBrokers: many("DiscussSidebarCategory", {
            inverse: "discussAsBrokers",
        }),
    },
    recordMethods: {
        async handleAddBrokerAutocompleteSource(req, res, broker_id) {
            this.discussView.update({addingChannelValue: req.term});
            const threads = await this.messaging.models.Thread.searchBrokersToOpen({
                limit: 10,
                searchTerm: req.term,
                broker_id,
            });
            const items = threads.map((thread) => {
                const escapedName = escape(thread.name);
                return {
                    id: thread.id,
                    label: escapedName,
                    value: escapedName,
                    broker_id: broker_id,
                };
            });
            res(items);
        },
        async handleAddBrokerAutocompleteSelect(ev, ui, broker_id) {
            // Necessary in order to prevent AutocompleteSelect event's default
            // behaviour as html tags visible for a split second in text area
            ev.preventDefault();
            const channel = this.messaging.models.Thread.insert({
                id: ui.item.id,
                model: "mail.channel",
                broker_id: broker_id,
            });
            await channel.join();
            // Channel must be pinned immediately to be able to open it before
            // the result of join is received on the bus.
            channel.update({isServerPinned: true});
            channel.open();
        },
    },
});
