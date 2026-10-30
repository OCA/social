import {Chatter} from "@mail/chatter/web_portal/chatter";
import {GatewayFollower} from "../gateway_follower/gateway_follower.esm";
import {onWillStart} from "@odoo/owl";
import {patch} from "@web/core/utils/patch";
import {user} from "@web/core/user";

patch(Chatter, {
    components: {...Chatter.components, GatewayFollower},
});

patch(Chatter.prototype, {
    setup() {
        super.setup(...arguments);
        this.user = user;
        onWillStart(async () => {
            this.hasGatewayGroup = await this.user.hasGroup(
                "mail_gateway.gateway_user"
            );
        });
    },
    toggleComposer(mode = false) {
        this.state.thread.composer.isGateway = mode === "gateway";
        super.toggleComposer(mode);
    },
});
