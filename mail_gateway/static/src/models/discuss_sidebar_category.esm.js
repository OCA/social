/** @odoo-module **/

import {attr, one} from "@mail/model/model_field";
import {clear} from "@mail/model/model_field_command";
import {registerPatch} from "@mail/model/model_core";

registerPatch({
    name: "DiscussSidebarCategory",
    fields: {
        gateway_id: attr({identifying: true}),
        gateway: one("Gateway", {inverse: "categories"}),
        discussAsGateways: one("Discuss", {
            inverse: "categoryGateways",
        }),
        hasAddCommand: {
            compute() {
                if (this.gateway_id) {
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
                    this.gateway_id &&
                    this.supportedChannelTypes.includes(channel.channel_type) &&
                    channel.thread.gateway_id !== this.gateway_id
                ) {
                    return clear();
                }
                return this._super();
            },
        },
        autocompleteMethod: {
            compute() {
                if (this.gateway_id) {
                    return "gateway";
                }
                return this._super();
            },
        },
        newItemPlaceholderText: {
            compute() {
                if (this.gateway_id) {
                    return this.env._t("Find a gateway channel...");
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
                if (this.gateway_id) {
                    return true;
                }
                return this._super();
            },
        },
        name: {
            compute() {
                if (this.gateway_id) {
                    return this.gateway.name;
                }
                return this._super();
            },
        },

        categoryItemsOrderedByLastAction: {
            compute() {
                if (this.gateway_id) {
                    return this.categoryItems;
                }
                return this._super();
            },
        },
        orderedCategoryItems: {
            compute() {
                if (this.gateway_id) {
                    return this.categoryItemsOrderedByLastAction;
                }
                return this._super();
            },
        },
        supportedChannelTypes: {
            compute() {
                if (this.gateway_id) {
                    return ["gateway"];
                }
                return this._super();
            },
        },
    },
    recordMethods: {
        onAddItemAutocompleteSource(req, res) {
            if (this.autocompleteMethod === "gateway") {
                this.messaging.discuss.handleAddGatewayAutocompleteSource(
                    req,
                    res,
                    this.gateway_id
                );
            }
            return this._super(...arguments);
        },

        onAddItemAutocompleteSelect(ev, ui) {
            if (this.autocompleteMethod === "gateway") {
                return this.messaging.discuss.handleAddGatewayAutocompleteSelect(
                    ev,
                    ui,
                    this.gateway_id
                );
            }
            return this._super(...arguments);
        },
    },
});
