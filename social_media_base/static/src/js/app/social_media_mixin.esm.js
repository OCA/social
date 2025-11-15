/** @odoo-module */

import {markup, useEffect} from "@odoo/owl";
import {session} from "@web/session";

export const SocialMediaMixin = (T) =>
    class extends T {
        /**
         * Validates whether the start date is less than or equal to the end date.
         *
         * @param {Date} startDate - The starting date of the range.
         * @param {Date} endDate - The ending date of the range.
         * @returns {Boolean} - Returns true if both dates are provided and the start date
         *                      is less than or equal to the end date, otherwise returns true
         *                      if either date is not provided.
         */
        validateRangeDate(startDate, endDate) {
            if (startDate && endDate) {
                return startDate <= endDate;
            }
            return true;
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
                            type === `social_${this.notif_view ?? "kanban"}_danger` &&
                            payload
                        ) {
                            message = markup(payload.message);
                            session.social_error = true;
                        }

                        if (
                            type === `social_${this.notif_view ?? "kanban"}_success` &&
                            payload
                        ) {
                            message = markup(payload.message);
                        }

                        if (
                            type === `social_${this.notif_view ?? "kanban"}_info` &&
                            payload
                        ) {
                            message = markup(payload.message);
                        }

                        if (type === "social_need_update" && payload) {
                            this.env.bus.trigger("SOCIAL:NEED-UPDATE", {
                                needUpdate: true,
                            });
                        }

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
