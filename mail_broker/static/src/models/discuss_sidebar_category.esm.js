/** @odoo-module **/

import {attr, one} from "@mail/model/model_field";
import {clear} from "@mail/model/model_field_command";
import {registerPatch} from "@mail/model/model_core";

registerPatch({
    name: "DiscussSidebarCategory",
    fields: {
        broker_id: attr({identifying: true}),
        broker_name: attr(),
        discussAsBrokers: one("Discuss", {
            inverse: "categoryBrokers",
        }),
        hasAddCommand: {
            compute() {
                if (this.broker_id) {
                    return true;
                }
                return this._super();
            },
        },
        activeItem: {
            compute() {
                // We need to adapt this function to refresh the right category only
                const channel =
                    this.messaging.discuss.activeThread &&
                    this.messaging.discuss.activeThread.channel;
                if (
                    channel &&
                    this.broker_id &&
                    this.supportedChannelTypes.includes(channel.channel_type) &&
                    channel.thread.broker_id !== this.broker_id
                ) {
                    return clear();
                }
                return this._super();
            },
        },
        autocompleteMethod: {
            compute() {
                if (this.broker_id) {
                    return "broker";
                }
                return this._super();
            },
        },
        newItemPlaceholderText: {
            compute() {
                if (this.broker_id) {
                    return this.env._t("Find a broker channel...");
                }
                return this._super();
            },
        },
        isServerOpen: {
            compute() {
                // There is no server state for non-users (guests)
                if (!this.messaging.currentUser) {
                    return clear();
                }
                if (!this.messaging.currentUser.res_users_settings_id) {
                    return clear();
                }
                if (this.broker_id) {
                    return true;
                }
                return this._super();
            },
        },
        name: {
            compute() {
                if (this.broker_id) {
                    return this.broker_name;
                }
                return this._super();
            },
        },

        categoryItemsOrderedByLastAction: {
            compute() {
                if (this.broker_id) {
                    return this.categoryItems;
                }
                return this._super();
            },
        },
        orderedCategoryItems: {
            compute() {
                if (this.broker_id) {
                    return this.categoryItemsOrderedByLastAction;
                }
                return this._super();
            },
        },
        supportedChannelTypes: {
            compute() {
                if (this.broker_id) {
                    return ["broker"];
                }
                return this._super();
            },
        },
    },
    recordMethods: {
        onAddItemAutocompleteSource(req, res) {
            if (this.autocompleteMethod === "broker") {
                this.messaging.discuss.handleAddBrokerAutocompleteSource(
                    req,
                    res,
                    this.broker_id
                );
            }
            return this._super(...arguments);
        },

        onAddItemAutocompleteSelect(ev, ui) {
            if (this.autocompleteMethod === "broker") {
                return this.messaging.discuss.handleAddBrokerAutocompleteSelect(
                    ev,
                    ui,
                    this.broker_id
                );
            }
            return this._super(...arguments);
        },
    },
});
