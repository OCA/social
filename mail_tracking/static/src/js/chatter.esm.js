/** @odoo-module **/

import {attr} from "@mail/model/model_field";
import {
    registerFieldPatchModel,
    registerInstancePatchModel,
} from "@mail/model/model_core";

registerInstancePatchModel(
    "mail.chatter",
    "mail/static/src/models/chatter/chatter.js",
    {
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
    }
);
registerFieldPatchModel("mail.chatter", "mail/static/src/models/chatter/chatter.js", {
    isMessageFailedBoxVisible: attr({
        default: true,
    }),
});
