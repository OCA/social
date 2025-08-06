import {Chatter} from "@mail/chatter/web_portal/chatter";
import {GatewayFollower} from "../gateway_follower/gateway_follower.esm";
import {patch} from "@web/core/utils/patch";

patch(Chatter, {
    components: {...Chatter.components, GatewayFollower},
});

patch(Chatter.prototype, {
    toggleComposer(mode = false) {
        this.state.thread.composer.isGateway = mode === "gateway";
        super.toggleComposer(mode);
    },
});
