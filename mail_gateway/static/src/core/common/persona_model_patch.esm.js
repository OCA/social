/** @odoo-module */

import {Persona} from "@mail/core/common/persona_model";
import {patch} from "@web/core/utils/patch";
import {Record} from "@mail/core/common/record";

patch(Persona.prototype, {
    setup() {
        super.setup();
        this.gateway_channels = Record.many("GatewayChannel");
    },
});
