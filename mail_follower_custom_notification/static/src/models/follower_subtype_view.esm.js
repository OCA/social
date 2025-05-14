/** @odoo-module **/

import {registerPatch} from "@mail/model/model_core";

registerPatch({
    name: "FollowerSubtypeView",
    recordMethods: {
        onChangeCustomNotification(ev) {
            this.subtype.update({customNotification: ev.target.value || null});
        },
    },
});
