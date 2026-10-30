import {Record} from "@mail/core/common/record";

export class GatewayChannel extends Record {
    static id = "id";
    /** @type {Object.<number, import("models").GatewayChannel>} */
    static records = {};
    /** @returns {import("models").GatewayChannel} */
    static get(data) {
        return super.get(data);
    }
    /** @returns {import("models").GatewayChannel|import("models").GatewayChannel[]} */
    static insert() {
        return super.insert(...arguments);
    }
    /** @type {Number} */
    id;
    /** @type {String} */
    name;
    gateway = Record.one("Gateway");
}
GatewayChannel.register();
