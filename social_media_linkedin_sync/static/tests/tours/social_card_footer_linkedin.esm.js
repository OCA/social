import {registry} from "@web/core/registry";

const CARD = ".o_kanban_record:contains('LinkedIn tour publication')";

registry.category("web_tour.tours").add("social_media_linkedin_sync.card_footer", {
    url: "/web#action=social_media_base.social_post_account_action",
    steps: () => [
        {
            content: "The card of the publication is drawn",
            trigger: CARD,
        },
        {
            content: "Its figures are drawn: this bridge imports them",
            trigger: `${CARD} div[name='likes']:contains('7')`,
        },
        {
            content: "The reaction is offered: this bridge answers it",
            trigger: `${CARD} .social-like-post`,
        },
        {
            content: "And so is the thread",
            trigger: `${CARD} .social-post-comment`,
        },
    ],
});
