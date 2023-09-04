/** @odoo-module **/

import {registerPatch} from "@mail/model/model_core";

registerPatch({
    name: "Chatter",
    recordMethods: {
        async refresh() {
            this._super(...arguments);
            if (this.thread) this.thread.refreshMessagefailed();
        },
        _onThreadIdOrThreadModelChanged() {
            this._super(...arguments);
            if (this.thread) this.thread.refreshMessagefailed();
        },
    },
});
