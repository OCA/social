/** @odoo-module **/

import {CalendarController} from "@web/views/calendar/calendar_controller";
import {_t} from "@web/core/l10n/translation";

export class SocialCalendarController extends CalendarController {
    /** @override */
    get editRecordDefaultDisplayText() {
        return _t("New Post");
    }
}
