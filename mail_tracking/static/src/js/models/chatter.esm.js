/** @odoo-module **/

import {attr} from "@mail/model/model_field";
import {registerPatch} from "@mail/model/model_core";

registerPatch({
    name: "Chatter",
    recordMethods: {
        async refresh() {
            this._super(...arguments);
            if (this.thread) this.thread.refreshMessagefailed();
        },
        toggleMessageFailedBoxVisibility() {
            this.update({
                isMessageFailedBoxVisible: !this.isMessageFailedBoxVisible,
            });
        },
        _onThreadIdOrThreadModelChanged() {
            this._super(...arguments);
            if (this.thread) this.thread.refreshMessagefailed();
        },
    },
    fields: {
        isMessageFailedBoxVisible: attr({
            default: true,
        }),
    },
});
