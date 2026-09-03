/** @odoo-module */

import {markup, useEffect} from "@odoo/owl";
import {session} from "@web/session";

export const SocialMediaMixin = (T) =>
    class extends T {
        handleSocialViewNotification(type, payload) {
            if (!payload) {
                return;
            }
            if (type === "social_need_update") {
                // The server also broadcasts the warning going down, so the
                // flag cannot be hardcoded here: a re-authorized account has
                // to clear the notice without reloading the page.
                this.env.bus.trigger("SOCIAL:NEED-UPDATE", {
                    needUpdate: payload.need_update ?? true,
                    accounts: payload.accounts ?? [],
                });
            }
            if (type === "social_posts_updated") {
                this.env.bus.trigger("SOCIAL:POSTS-UPDATED", payload);
            }
        }

        enableSocialNotifications() {
            session.social_error = false;
            const handleNotification = ({detail: notifications}) => {
                if (notifications && notifications.length > 0) {
                    notifications.forEach((notif) => {
                        const {payload, type} = notif;
                        let message = null;
                        const sticky = false;
                        if (
                            type === `social_${this.notifView ?? "kanban"}_danger` &&
                            payload
                        ) {
                            message = markup(payload.message);
                            session.social_error = true;
                        }

                        if (
                            type === `social_${this.notifView ?? "kanban"}_success` &&
                            payload
                        ) {
                            message = markup(payload.message);
                        }

                        if (
                            type === `social_${this.notifView ?? "kanban"}_info` &&
                            payload
                        ) {
                            message = markup(payload.message);
                        }

                        this.handleSocialViewNotification(type, payload);

                        if (type && message !== null) {
                            this.notificationService.add(message, {
                                type: payload.message_type,
                                sticky: sticky,
                            });
                        }
                    });
                }
            };
            useEffect(() => {
                this.busService.addEventListener("notification", handleNotification);
                return () => {
                    this.busService.removeEventListener(
                        "notification",
                        handleNotification
                    );
                };
            });
        }
    };
