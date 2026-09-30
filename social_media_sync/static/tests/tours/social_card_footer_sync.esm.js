/** @odoo-module */

import {registry} from "@web/core/registry";

const CARD = ".o_kanban_record:contains('Publication without bridge')";

/**
 * A social media no bridge serves: this module holds the thread and the
 * reactions, but nothing answers them for that social media and nothing
 * imports its figures, so the footer of the card says none of the three.
 */
registry.category("web_tour.tours").add("social_media_sync.card_footer", {
    test: true,
    url: "/web#action=social_media_base.social_post_account_action",
    steps: () => [
        {
            content: "The card of the publication is drawn",
            trigger: CARD,
            isCheck: true,
        },
        {
            content: "No figures: nothing imports them for this social media",
            trigger: `${CARD}:not(:has(div[name='likes']))`,
            isCheck: true,
        },
        {
            content: "And neither entry, because nothing would answer them",
            trigger: `${CARD}:not(:has(.social-like-post)):not(:has(.social-post-comment))`,
            isCheck: true,
        },
    ],
});
