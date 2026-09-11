/** @odoo-module **/

import {SocialCalendarController} from "./social_calendar_controller.esm";
import {calendarView} from "@web/views/calendar/calendar_view";
import {registry} from "@web/core/registry";

export const SocialCalendarView = {
    ...calendarView,
    Controller: SocialCalendarController,
};

registry.category("views").add("social_calendar", SocialCalendarView);
