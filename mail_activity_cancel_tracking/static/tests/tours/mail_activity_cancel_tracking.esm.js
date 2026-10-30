import {registry} from "@web/core/registry";

registry.category("web_tour.tours").add("mail_activity_cancel_tracking_done", {
    test: true,
    steps: () => [
        {
            trigger: ".o-mail-Chatter",
        },
        {
            trigger: "button.o-mail-Activity-markDone",
            run: "click",
        },
        {
            trigger: "button[aria-label='Done']",
            run: "click",
        },
        {
            trigger: ".o-mail-Message:contains('done'):contains('Play Mario Kart')",
        },
    ],
});
registry.category("web_tour.tours").add("mail_activity_cancel_tracking_cancel", {
    test: true,
    steps: () => [
        {
            trigger: ".o-mail-Chatter",
        },
        {
            trigger: ".o-mail-Activity button.btn-danger:contains('Cancel')",
            run: "click",
        },
        {
            trigger: ".o-mail-Message:contains('canceled'):contains('Play Mario Kart')",
        },
    ],
});
