/** @odoo-module **/

import {attr, many} from "@mail/model/model_field";
import {registerModel} from "@mail/model/model_core";

registerModel({
    name: "MessageFailed",
    modelMethods: {
        /**
         * @param {Object} data
         * @returns {Object}
         */
        convertData(data) {
            const data2 = {};
            if ("author" in data) {
                if (!data.author) {
                    data2.author = [["unlink-all"]];
                } else if (data.author) {
                    data2.author = data.author[1];
                    data2.author_id = data.author[0];
                }
            }
            if ("body" in data) {
                data2.body = data.body;
            }
            if ("date" in data) {
                data2.date = data.date;
            }
            if ("failed_recipients" in data) {
                data2.failed_recipients = data.failed_recipients;
            }
            if ("id" in data) {
                data2.id = data.id;
            }
            return data2;
        },
    },
    fields: {
        thread: many("Thread", {
            inverse: "messagefailed",
        }),
        body: attr(),
        author: attr(),
        author_id: attr(),
        date: attr(),
        failed_recipients: attr(),
        id: attr({
            readonly: true,
            required: true,
        }),
    },
});
