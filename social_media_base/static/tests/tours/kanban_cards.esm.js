import {delay, queryFirst} from "@odoo/hoot-dom";
import {registry} from "@web/core/registry";

// A card drawn from a `card` template: the cards of the legacy templates carry
// this class on top of `o_kanban_record`.
const CARD = ".o_kanban_record:not(.o_legacy_kanban_record)";

/**
 * Wait for an image to load and answer the height its width gives with the
 * proportions of the file.
 */
async function proportionalHeight(img) {
    if (!img.complete) {
        await new Promise((resolve) =>
            img.addEventListener("load", resolve, {once: true})
        );
    }
    return Math.round((img.offsetWidth * img.naturalHeight) / img.naturalWidth);
}

/** Fail when clicking a card opened a dialog on its record. */
async function noDialog() {
    // The dialog opens once the form of the record is loaded.
    await delay(1000);
    if (queryFirst(".modal")) {
        throw new Error("Clicking the card opened a dialog on its record.");
    }
}

/**
 * Every kanban card of the module, drawn from its `card` template: the social
 * media, the post, the publication of the dashboard and the post inside its
 * campaign. The publication has no address, so opening it says it is gone
 * instead of opening anything on the social media. The logo of the social
 * media keeps its proportions, and the cards of the publications of a post
 * open nothing.
 */
registry.category("web_tour.tours").add("social_media_base.kanban_cards", {
    url: "/odoo/social-media",
    steps: () => [
        {
            content: "The card of the social media shows its image",
            trigger: `${CARD}:contains('Media of the cards') .o_field_image img`,
        },
        {
            content: "The logo is as tall as the proportions of the image give",
            trigger: `${CARD}:contains('Media of the cards') .o_field_image img`,
            async run() {
                const img = this.anchor;
                const height = await proportionalHeight(img);
                if (img.offsetWidth !== 100 || img.offsetHeight !== height) {
                    throw new Error(
                        `The logo is drawn ${img.offsetWidth}x${img.offsetHeight}, not 100x${height}.`
                    );
                }
            },
        },
        {
            content: "Open the posts",
            trigger: "a[data-menu-xmlid='social_media_base.social_post_menu']",
            run: "click",
        },
        {
            content: "The card of the post is drawn",
            trigger: `.o_kanban_view ${CARD}:contains('Publication of the cards')`,
        },
        {
            content: "Open the post",
            trigger: `.o_kanban_view ${CARD}:contains('Publication of the cards')`,
            run: "click",
        },
        {
            content: "Click the card of a publication of the post",
            trigger: `.o_form_view .o_field_x2many ${CARD}:contains('Publication of the cards') .o_field_widget[name='state']`,
            run: "click",
        },
        {
            content: "The card of the publication opens nothing",
            trigger: `.o_form_view .o_field_x2many ${CARD}:contains('Publication of the cards')`,
            run: noDialog,
        },
        {
            content: "Open the dashboard",
            trigger: "a[data-menu-xmlid='social_media_base.social_dashboard_menu']",
            run: "click",
        },
        {
            content: "The card of the publication is drawn",
            trigger: `${CARD}.oe_kanban_social_dashboard:contains('Publication of the cards')`,
        },
        {
            content: "Open the publication, which has no address",
            trigger: `${CARD}.oe_kanban_social_dashboard:contains('Publication of the cards')`,
            run: "click",
        },
        {
            content: "It says the publication is gone",
            trigger:
                ".o_notification:contains('The post does not exist or has been deleted.')",
        },
        {
            content: "Open the campaigns",
            trigger: "a[data-menu-xmlid='social_media_base.utm_campaign_menu']",
            run: "click",
        },
        {
            content: "Open the campaign of the post",
            trigger: ".o_data_row:contains('Campaign of the cards') .o_data_cell",
            run: "click",
        },
        {
            content: "Open the tab of its posts",
            trigger: ".o_notebook_headers a[name='social_media']",
            run: "click",
        },
        {
            content: "The card of the post is drawn inside the campaign",
            trigger: `.o_form_view .o_field_x2many ${CARD}:contains('Post of the campaign')`,
        },
    ],
});

/**
 * The images of a publication keep their proportions, and the cards of its
 * images and videos open nothing. The dashboard opens no publication, so the
 * tour starts on its form.
 */
registry.category("web_tour.tours").add("social_media_base.kanban_cards_medias", {
    steps: () => [
        {
            content: "The image keeps its proportions",
            trigger: `.o_form_view .o_field_widget[name='image_ids'] ${CARD} img`,
            async run() {
                const img = this.anchor;
                const height = await proportionalHeight(img);
                if (img.offsetHeight !== height) {
                    throw new Error(
                        `The image is drawn ${img.offsetWidth}x${img.offsetHeight}, not ${img.offsetWidth}x${height}.`
                    );
                }
            },
        },
        {
            content: "Click the image of the publication",
            trigger: `.o_form_view .o_field_widget[name='image_ids'] ${CARD} img`,
            run: "click",
        },
        {
            content: "The card of the image opens nothing",
            trigger: `.o_form_view .o_field_widget[name='image_ids'] ${CARD}`,
            run: noDialog,
        },
        {
            content: "Click the video of the publication",
            trigger: `.o_form_view .o_field_widget[name='video_ids'] ${CARD} video`,
            run: "click",
        },
        {
            content: "The card of the video opens nothing",
            trigger: `.o_form_view .o_field_widget[name='video_ids'] ${CARD}`,
            run: noDialog,
        },
    ],
});
