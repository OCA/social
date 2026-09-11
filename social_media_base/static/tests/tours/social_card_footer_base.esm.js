/** @odoo-module */

import {registry} from "@web/core/registry";

const CARD = ".o_kanban_record:contains('Publication of the matrix')";

/**
 * The card of a publication in an installation that cannot say anything about
 * what the social media reported: no synchronization module, or none for that
 * social media. Meant to be run against such an installation, which is why
 * its test is out of the standard suite.
 */
registry.category("web_tour.tours").add("social_media_base.card_footer_matrix", {
    test: true,
    url: "/web#action=social_media_base.social_post_account_action",
    steps: () => [
        {
            content: "The card of the publication is drawn",
            trigger: CARD,
            isCheck: true,
        },
        {
            content: "Without figures, which nothing here imports",
            trigger: `${CARD}:not(:has(div[name='likes']))`,
            isCheck: true,
        },
        {
            content: "And without entries, which nothing here answers",
            trigger: `${CARD}:not(:has(.social-like-post)):not(:has(.social-post-comment))`,
            isCheck: true,
        },
    ],
});
