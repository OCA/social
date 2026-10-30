/* @odoo-module */
import {Gateway} from "../../models/gateway.esm";
import {Store} from "@mail/core/common/store_service";
import {patch} from "@web/core/utils/patch";

/** @type {import("models").Store} */
const storePatch = {
    setup() {
        super.setup(...arguments);
        /** @type {typeof import("@mail_gateway/models/gateway").Gateway} */
        this.Gateway = Gateway;
    },
};
patch(Store.prototype, storePatch);
