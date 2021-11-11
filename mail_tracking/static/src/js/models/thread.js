odoo.define("mail_tracking/static/src/js/models/thread.js", function (require) {
    "use strict";

    const {registerNewModel} = require("mail/static/src/model/model_core.js");
    const {attr, many2one} = require("mail/static/src/model/model_field.js");

    function factory(dependencies) {
        class MessageFailed extends dependencies["mail.model"] {
            static convertData(data) {
                const data2 = {};
                if ("author" in data) {
                    if (!data.author) {
                        data2.author = [["unlink-all"]];
                    } else {
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
            }
        }

        MessageFailed.fields = {
            thread: many2one("mail.thread", {
                inverse: "messagefailed",
            }),
            body: attr(),
            author: attr(),
            author_id: attr(),
            date: attr(),
            failed_recipients: attr(),
            id: attr(),
        };

        MessageFailed.modelName = "mail.message.failed";

        return MessageFailed;
    }

    registerNewModel("mail.message.failed", factory);
});
