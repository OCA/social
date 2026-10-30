import {Persona} from "@mail/core/common/persona_model";
import {Record} from "@mail/core/common/record";
import {patch} from "@web/core/utils/patch";

patch(Persona.prototype, {
    setup() {
        super.setup();
        this.gateway_channels = Record.many("GatewayChannel");
    },
});
