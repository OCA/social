/** @odoo-module */

import {registry} from "@web/core/registry";

const CARD = ".o_kanban_record:contains('X reaction publication')";
const ENTRY = `${CARD} .social-like-post`;

registry.category("web_tour.tours").add("social_media_x_sync.post_reaction", {
    test: true,
    url: "/web#action=social_media_base.social_post_account_action",
    steps: () => [
        {
            content: "The entry offers the like, so nothing is recommended yet",
            trigger: `${ENTRY} .fa-thumbs-o-up`,
            isCheck: true,
        },
        {
            content: "Press it to like the publication",
            trigger: ENTRY,
            run: "click",
        },
        {
            content: "The card says the account now likes it",
            trigger: `${ENTRY} .fa-thumbs-up`,
            isCheck: true,
        },
        {
            content: "Press it again to withdraw the like",
            trigger: ENTRY,
            run: "click",
        },
        {
            content: "The like is offered again, so it was withdrawn",
            trigger: `${ENTRY} .fa-thumbs-o-up`,
            isCheck: true,
        },
    ],
});
