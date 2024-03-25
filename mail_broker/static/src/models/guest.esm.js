/** @odoo-module **/
import {attr} from "@mail/model/model_field";
import {registerPatch} from "@mail/model/model_core";

registerPatch({
    name: "Guest",
    fields: {
        broker_id: attr(),
    },
});
