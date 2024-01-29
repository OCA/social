/** @odoo-module **/

import {attr, many} from "@mail/model/model_field";
import {registerModel} from "@mail/model/model_core";

registerModel({
    name: "Gateway",
    fields: {
        id: attr({identifying: true}),
        name: attr(),
        type: attr(),
        categories: many("DiscussSidebarCategory", {
            inverse: "gateway",
        }),
    },
});
