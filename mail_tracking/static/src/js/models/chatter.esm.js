/** @odoo-module **/

import {attr, one} from "@mail/model/model_field";
import {registerPatch} from "@mail/model/model_core";

registerPatch({
    name: "Chatter",
    modelMethods: {
        async refresh() {
            this._super(...arguments);
            this.thread.refreshMessagefailed();
        },
        toggleMessageFailedBoxVisibility() {
            this.update({
                isMessageFailedBoxVisible: !this.isMessageFailedBoxVisible,
            });
        },
        _onThreadIdOrThreadModelChanged() {
            this._super(...arguments);
            this.thread.refreshMessagefailed();
        },
    },
    fields: {
        isMessageFailedBoxVisible: attr({
            default: true,
        }),
        threadViewFailed: one("ThreadView", {
            related: "threadViewer.threadView",
        }),
    },
});
