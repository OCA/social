/** @odoo-module */

import {markup} from "@odoo/owl";
import {session} from "@web/session";
import {useBus} from "@web/core/utils/hooks";

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
            // Composed from `notifView` so a view listening on types of its
            // own only has to set it, without a change on the server side.
            const view = this.notifView ?? "kanban";
            const dangerType = `social_${view}_danger`;
            // The success type is not emitted today; it stays listed because
            // the three of them are the same contract with the server.
            const toastTypes = [
                dangerType,
                `social_${view}_success`,
                `social_${view}_info`,
            ];
            useBus(this.busService, "notification", ({detail: notifications}) => {
                for (const {payload, type} of notifications || []) {
                    const message =
                        payload && toastTypes.includes(type)
                            ? markup(payload.message)
                            : null;
                    if (message !== null && type === dangerType) {
                        session.social_error = true;
                    }

                    this.handleSocialViewNotification(type, payload);

                    if (type && message !== null) {
                        this.notificationService.add(message, {
                            type: payload.message_type,
                            sticky: false,
                        });
                    }
                }
            });
        }
    };
