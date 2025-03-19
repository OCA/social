/** @odoo-module **/
import {Chatter} from "@mail/core/web/chatter";
import {patch} from "@web/core/utils/patch";
import {GatewayFollower} from "../gateway_follower/gateway_follower.esm";

patch(Chatter, {
    components: {...Chatter.components, GatewayFollower},
});

patch(Chatter.prototype, {
    toggleComposer(mode = false) {
        this.state.thread.composer.isGateway = mode === "gateway";
        super.toggleComposer(mode);
    },
});
