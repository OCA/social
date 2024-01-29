/** @odoo-module **/

import {clear} from "@mail/model/model_field_command";
import {one} from "@mail/model/model_field";
import {registerPatch} from "@mail/model/model_core";

registerPatch({
    name: "ComposerView",
    recordMethods: {
        _getMessageData() {
            var result = this._super(...arguments);
            if (this.composer.isGateway) {
                result.gateway_notifications =
                    this.composer.composerGatewayFollowers.map((follower) => {
                        return follower._getMessageData();
                    });
            }
            return result;
        },
    },
    fields: {
        hasFollowers: {
            compute() {
                if (this.composer.isGateway) {
                    return false;
                }
                return this._super();
            },
        },
        hasHeader: {
            compute() {
                return Boolean(this._super() || this.composer.isGateway);
            },
        },
        isExpandable: {
            /*
                We will not allow to expand on this composer due to all complexity of selection
            */
            compute() {
                if (this.composer.isGateway) {
                    return clear();
                }
                return this._super();
            },
        },
        composerGatewayChannelView: one("GatewayChannelView", {
            compute() {
                if (this.composer.isGateway) {
                    return {};
                }
                return clear();
            },
            inverse: "composerViewOwner",
        }),
    },
});
