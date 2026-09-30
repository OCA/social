/** @odoo-module */

import {registry} from "@web/core/registry";

const PANEL = ".o_content";
// Asserted before every negative check: the account bar is loaded after the
// first paint, so a dashboard that has not drawn it yet would answer that
// there is no notice for the same reason it answers that there is no card.
const CARD = `${PANEL} .shadow:contains('Notices account')`;
const CREDENTIALS = `${PANEL} .alert-warning:contains('are no longer valid')`;
const IMPORT = `${PANEL} .alert-info:contains('has new publications')`;

/**
 * Expired credentials alone: what the account is waiting for is a new
 * authorization, and nothing says its publications are behind.
 */
registry
    .category("web_tour.tours")
    .add("social_media_sync.account_notices_credentials", {
        test: true,
        url: "/web#action=social_media_base.social_post_account_action",
        steps: () => [
            {
                content: "The card of the account is drawn",
                trigger: CARD,
                isCheck: true,
            },
            {
                content: "The credentials are announced, naming the account",
                trigger: `${CREDENTIALS}:contains('Notices account')`,
                isCheck: true,
            },
            {
                content: "And nothing announces an import",
                trigger: `${PANEL}:not(:has(.alert-info))`,
                isCheck: true,
            },
        ],
    });

/**
 * Publications to import alone: the token works, and what resolves the state
 * is the *Update* button and not an authorization.
 */
registry.category("web_tour.tours").add("social_media_sync.account_notices_import", {
    test: true,
    url: "/web#action=social_media_base.social_post_account_action",
    steps: () => [
        {
            content: "The card of the account is drawn",
            trigger: CARD,
            isCheck: true,
        },
        {
            content: "The import is announced, naming the account",
            trigger: `${IMPORT}:contains('Notices account')`,
            isCheck: true,
        },
        {
            content: "And nothing says the credentials expired",
            trigger: `${PANEL}:not(:has(.alert-warning))`,
            isCheck: true,
        },
    ],
});

/**
 * Both at once: neither state implies the other, so the card says the two
 * things it has to say instead of choosing one.
 */
registry.category("web_tour.tours").add("social_media_sync.account_notices_both", {
    test: true,
    url: "/web#action=social_media_base.social_post_account_action",
    steps: () => [
        {
            content: "The card of the account is drawn",
            trigger: CARD,
            isCheck: true,
        },
        {
            content: "The credentials are announced",
            trigger: CREDENTIALS,
            isCheck: true,
        },
        {
            content: "And so is the import, with its own text",
            trigger: IMPORT,
            isCheck: true,
        },
    ],
});

/**
 * The *Update* button when it refreshed the figures and found no account to
 * import from. Announcing publications it did not bring in is what would make
 * the button look broken the next time an account really is behind.
 */
registry
    .category("web_tour.tours")
    .add("social_media_sync.update_without_new_publications", {
        test: true,
        url: "/web#action=social_media_base.social_post_account_action",
        steps: () => [
            {
                content: "The card of the account is drawn",
                trigger: CARD,
                isCheck: true,
            },
            {
                content: "The user asks for an update",
                trigger: "button.o_kanban_statistics_refresh_now",
            },
            {
                content: "And is told that the figures moved and the feed did not",
                trigger:
                    ".o_notification .o_notification_content:contains('The data was updated. No new publications.')",
                isCheck: true,
            },
        ],
    });

/** Neither: an account nothing is pending on carries no notice at all. */
registry.category("web_tour.tours").add("social_media_sync.account_notices_none", {
    test: true,
    url: "/web#action=social_media_base.social_post_account_action",
    steps: () => [
        {
            content: "The card of the account is drawn",
            trigger: CARD,
            isCheck: true,
        },
        {
            content: "And the dashboard announces nothing about it",
            trigger: `${PANEL}:not(:has(.alert-warning)):not(:has(.alert-info))`,
            isCheck: true,
        },
    ],
});
