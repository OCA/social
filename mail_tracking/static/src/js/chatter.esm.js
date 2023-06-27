/** @odoo-module **/

import { registerPatch } from '@mail/model/model_core';
import {attr} from "@mail/model/model_field";

registerPatch({
    name: 'Chatter',
    fields: {
        isMessageFailedBoxVisible: attr({
            default: false,
        }),
    },
    recordMethods: {
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
});
