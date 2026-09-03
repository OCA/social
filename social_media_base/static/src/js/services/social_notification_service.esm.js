/** @odoo-module **/

import {markup} from "@odoo/owl";
import {registry} from "@web/core/registry";
import {session} from "@web/session";

/** Displays the notification left in the session by an OAuth callback. */
export const socialNotificationService = {
    dependencies: ["notification"],
    start(env, {notification}) {
        const pending = session.social_media_notification;
        if (!pending || !pending.message) {
            return;
        }
        delete session.social_media_notification;
        const type = pending.message_type || "danger";
        notification.add(markup(pending.message), {
            type: type,
            sticky: type === "danger",
        });
    },
};

registry
    .category("services")
    .add("social_media_notification", socialNotificationService);
