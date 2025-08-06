import {Record} from "@mail/core/common/record";

export class GatewayFollower extends Record {
    static id = "id";
    /** @type {Object.<number, import("models").GatewayFollower>} */
    static records = {};
    /** @returns {import("models").GatewayFollower} */
    static get(data) {
        return super.get(data);
    }
    /** @returns {import("models").GatewayFollower|import("models").GatewayFollower[]} */
    static insert() {
        return super.insert(...arguments);
    }
    /** @type {Number} */
    id;
    /** @type {String} */
    name;
    partner = Record.one("Persona");
    channel = Record.one("GatewayChannel");
}

GatewayFollower.register();
