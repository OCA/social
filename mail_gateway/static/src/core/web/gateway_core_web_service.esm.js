/* @odoo-module */
import {reactive} from "@odoo/owl";
import {registry} from "@web/core/registry";

export class GatewayCoreWeb {
    constructor(env, services) {
        Object.assign(this, {
            busService: services.bus_service,
        });
        /** @type {import("@mail/core/common/messaging_service").Messaging} */
        this.messagingService = services["mail.messaging"];
        /** @type {import("@mail/core/common/store_service").Store} */
        this.store = services["mail.store"];
    }
    setup() {
        this.messagingService.isReady.then((data) => {
            if (data.current_user_settings?.is_discuss_sidebar_category_gateway_open) {
                this.store.discuss.gateway.isOpen = true;
            }
            this.busService.subscribe("res.users.settings", (payload) => {
                if (payload) {
                    this.store.discuss.gateway.isOpen =
                        payload.is_discuss_sidebar_category_gateway_open ??
                        this.store.discuss.gateway.isOpen;
                }
            });
        });
    }
}

export const gatewayCoreWeb = {
    dependencies: ["bus_service", "mail.messaging", "mail.store"],
    start(env, services) {
        const gatewayCoreWeb = reactive(new GatewayCoreWeb(env, services));
        gatewayCoreWeb.setup();
        return gatewayCoreWeb;
    },
};

registry.category("services").add("mail_gateway.core.web", gatewayCoreWeb);
