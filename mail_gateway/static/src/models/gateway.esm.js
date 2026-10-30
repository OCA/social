/** @odoo-module **/
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
    /** @type {number} */
    id;
    /** @type {string} */
    type;
    /** @type {string} */
    name;
}
Gateway.register();
