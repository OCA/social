/** @odoo-module */

import {registry} from "@web/core/registry";

const CARD = ".o_kanban_record:contains('X tour publication')";

registry.category("web_tour.tours").add("social_media_x_sync.card_footer", {
    test: true,
    url: "/web#action=social_media_base.social_post_account_action",
    steps: () => [
        {
            content: "The card of the publication is drawn",
            trigger: CARD,
            isCheck: true,
        },
        {
            content: "Its figures are drawn: this bridge imports them",
            trigger: `${CARD} div[name='likes']:contains('7')`,
            isCheck: true,
        },
        {
            content: "The thread is offered: this bridge answers it",
            trigger: `${CARD} .social-post-comment`,
            isCheck: true,
        },
        {
            content: "The reaction is not: X serves none",
            trigger: `${CARD}:not(:has(.social-like-post))`,
            isCheck: true,
        },
    ],
});
