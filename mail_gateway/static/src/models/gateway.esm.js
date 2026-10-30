import {Record} from "@mail/core/common/record";

export class Gateway extends Record {
    static id = "id";
    /** @type {Object.<number, import("models").Gateway>} */
    static records = {};
    /** @returns {import("models").Gateway} */
    static get(data) {
        return super.get(data);
    }
    /** @returns {import("models").Gateway|import("models").Gateway[]} */
    static insert() {
        return super.insert(...arguments);
    }
    /** @type {Number} */
    id;
    /** @type {String} */
    type;
    /** @type {String} */
    name;
}
Gateway.register();
