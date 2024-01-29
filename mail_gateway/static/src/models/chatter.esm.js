/** @odoo-module **/

import {clear} from "@mail/model/model_field_command";
import {registerPatch} from "@mail/model/model_core";

registerPatch({
    name: "Chatter",
    recordMethods: {
        onClickLogNote() {
            if (this.composerView && this.composerView.composer.isGateway) {
                this.update({composerView: clear()});
            }
            this._super(...arguments);
            if (this.composerView) {
                this.composerView.composer.update({isGateway: false});
            }
        },
        onClickSendMessage() {
            if (this.composerView && this.composerView.composer.isGateway) {
                this.update({composerView: clear()});
            }
            this._super(...arguments);
            if (this.composerView) {
                this.composerView.composer.update({isGateway: false});
            }
        },
        onClickGatewayMessage() {
            if (this.composerView && this.composerView.composer.isGateway) {
                this.update({composerView: clear()});
            } else {
                this.showGatewayComposerView();
            }
        },
        showGatewayComposerView() {
            this.update({composerView: {}});
            this.composerView.composer.update({isLog: false, isGateway: true});
            this.focus();
        },
    },
    fields: {},
});
