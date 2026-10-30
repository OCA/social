/** @odoo-module **/

import {markup} from "@odoo/owl";
import {registry} from "@web/core/registry";
import {session} from "@web/session";

/**
 * Displays the notifications of the social media modules.
 *
 * Two sources, one service: what an OAuth callback left in the session,
 * which is delivered on the next page load because the redirect of the
 * callback would outrun a bus message, and what the server pushes through
 * the bus from an action of a form. Listening from the service and not from
 * a renderer keeps a view type from having to exist only to reach the bus.
 *
 * A failure of a form travels through the session, which is where the OAuth
 * callbacks leave it, so the types subscribed to are the two the server
 * pushes: the success and the information of an action of the client.
 */
export const socialNotificationService = {
    dependencies: ["bus_service", "notification"],
    start(env, {bus_service: busService, notification}) {
        // A permanent service, so the subscription needs no cleanup.
        const showFormNotification = (payload) => {
            if (!payload?.message) {
                return;
            }
            notification.add(markup(payload.message), {
                type: payload.message_type,
                sticky: false,
            });
        };
        busService.subscribe("social_form_info", showFormNotification);
        busService.subscribe("social_form_success", showFormNotification);
        const pending = session.social_media_notification;
        if (!pending || !pending.length) {
            return;
        }
        delete session.social_media_notification;
        for (const notif of pending) {
            if (!notif.message) {
                continue;
            }
            const type = notif.message_type || "danger";
            notification.add(markup(notif.message), {
                type: type,
                sticky: type === "danger",
            });
        }
    },
};

registry
    .category("services")
    .add("social_media_notification", socialNotificationService);
