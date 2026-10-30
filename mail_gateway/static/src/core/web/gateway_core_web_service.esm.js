import {reactive} from "@odoo/owl";
import {registry} from "@web/core/registry";
import {user} from "@web/core/user";

export class GatewayCoreWeb {
    constructor(env, services) {
        Object.assign(this, {
            busService: services.bus_service,
        });
        /** @type {import("@mail/core/common/store_service").Store} */
        this.store = services["mail.store"];
    }
    setup() {
        if (user.settings?.is_discuss_sidebar_category_gateway_open) {
            this.store.discuss.gateway.isOpen = true;
        }
        this.busService.subscribe("res.users.settings", (payload) => {
            if (payload) {
                this.store.discuss.gateway.isOpen =
                    payload.is_discuss_sidebar_category_gateway_open ??
                    this.store.discuss.gateway.isOpen;
            }
        });
    }
}

export const gatewayCoreWeb = {
    dependencies: ["bus_service", "mail.store"],
    start(env, services) {
        const gateway_core_web = reactive(new GatewayCoreWeb(env, services));
        gateway_core_web.setup();
        return gateway_core_web;
    },
};

registry.category("services").add("mail_gateway.core.web", gatewayCoreWeb);
