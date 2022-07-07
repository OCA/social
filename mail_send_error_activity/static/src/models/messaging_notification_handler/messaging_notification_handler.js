odoo.define(
    "mail_send_error_activity/static/src/models/messaging_notification_handler/messaging_notification_handler.js",
    function (require) {
        "use strict";

        const {
            registerInstancePatchModel,
        } = require("mail/static/src/model/model_core.js");

        registerInstancePatchModel(
            "mail.messaging_notification_handler",
            "mail_send_error_activity/static/src/models/messaging_notification_handler/messaging_notification_handler.js",
            {
                /**
                 * @private
                 * @param {Object} data
                 * @param {String} [data.info]
                 * @param {String} [data.type]
                 */
                async _handleNotificationPartner(data) {
                    const {type, elements} = data;
                    if (type === "message_notification_update") {
                        await this._handleRefreshActivities(elements);
                        return this._handleNotificationPartnerMessageNotificationUpdate(
                            elements
                        );
                    }
                    return this._super(data);
                },

                /**
                 * @private
                 * @param {Object[]} elements
                 */
                async _handleRefreshActivities(elements) {
                    for (const index in elements) {
                        var element = elements[index];
                        const thread = await this.env.models[
                            "mail.thread"
                        ].findFromIdentifyingData({
                            id: element.res_id,
                            model: element.model,
                        });
                        await thread.refreshActivities();
                        thread.refresh();
                    }
                },
            }
        );
    }
);
