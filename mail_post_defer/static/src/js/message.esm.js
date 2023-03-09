/** @odoo-module **/
import {
    registerFieldPatchModel,
    registerInstancePatchModel,
} from "@mail/model/model_core";
import {attr} from "@mail/model/model_field";

registerInstancePatchModel("mail.message", "mail_post_defer.message", {
    xmlDependencies: ["/mail_post_defer/static/src/xml/message.xml"],

    /**
     * Allow deleting deferred messages
     *
     * @param {Boolean} editing Set `true` to know if you can edit the message
     * @returns {Boolean}
     */
    _computeCanBeDeleted(editing) {
        return (
            this._super() ||
            (!editing &&
                this.notifications.filter(
                    (current) => current.notification_status !== "ready"
                ).length === 0)
        );
    },

    /**
     * Allow editing messages.
     *
     * Upstream Odoo allows editing any message that can be deleted. We do the
     * same here. However, if the message is a public message that is deferred,
     * it can be edited but not deleted.
     *
     * @returns {Boolean}
     */
    _computeCanBeEdited() {
        return this._computeCanBeDeleted(true);
    },
});

registerFieldPatchModel("mail.message", "mail_post_defer.message", {
    /**
     * Whether this message can be edited.
     */
    canBeEdited: attr({
        compute: "_computeCanBeEdited",
    }),
});
