/** @odoo-module **/
import {Chatter} from "@mail/core/web/chatter";
import {GatewayFollower} from "../gateway_follower/gateway_follower.esm";
import {onWillStart} from "@odoo/owl";
import {patch} from "@web/core/utils/patch";
import {useService} from "@web/core/utils/hooks";

patch(Chatter, {
    components: {...Chatter.components, GatewayFollower},
});

patch(Chatter.prototype, {
    setup() {
        super.setup(...arguments);
        this.user = useService("user");
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
