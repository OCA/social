/* @odoo-module */

import {registry} from "@web/core/registry";

registry.category("web_tour.tours").add("mail_activity_cancel_tracking_done", {
    test: true,
    steps: () => [
        {
            trigger: ".o-mail-Activity span:contains('Mark Done')",
        },
        {
            trigger: ".o-mail-ActivityMarkAsDone button[aria-label='Done']",
        },
        {
            trigger: ".o-mail-Message:contains('done'):contains('Play Mario Kart')",
            isCheck: true,
        },
    ],
});
registry.category("web_tour.tours").add("mail_activity_cancel_tracking_cancel", {
    test: true,
    steps: () => [
        {
            trigger: ".o-mail-Activity span:contains('Cancel')",
        },
        {
            trigger: ".o-mail-Message:contains('canceled'):contains('Play Mario Kart')",
            isCheck: true,
        },
    ],
});
