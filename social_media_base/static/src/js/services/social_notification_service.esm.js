/** @odoo-module **/

import {markup} from "@odoo/owl";
import {registry} from "@web/core/registry";
import {session} from "@web/session";

/**
 * Displays the notification left by a social media OAuth callback.
 *
 * The callbacks answer with a redirect, so a message sent through the bus at
 * that moment is lost: the web client is reloading. The server keeps it in the
 * session instead and hands it over in the session information, and this
 * service shows it once when the client starts.
 *
 * The message is built by the server and rendered as markup, like the ones of
 * the bus, so that it can carry links.
 */
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
