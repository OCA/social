import {registry} from "@web/core/registry";
import {rpc} from "@web/core/network/rpc";

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
        url: "/web#action=social_media_base.social_post_account_action",
        steps: () => [
            {
                content: "The card of the account is drawn",
                trigger: CARD,
            },
            {
                content: "The credentials are announced, naming the account",
                trigger: `${CREDENTIALS}:contains('Notices account')`,
            },
            {
                content: "And nothing announces an import",
                trigger: `${PANEL}:not(:has(.alert-info))`,
            },
        ],
    });

/**
 * Publications to import alone: the token works, and what resolves the state
 * is the *Update* button and not an authorization.
 */
registry.category("web_tour.tours").add("social_media_sync.account_notices_import", {
    url: "/web#action=social_media_base.social_post_account_action",
    steps: () => [
        {
            content: "The card of the account is drawn",
            trigger: CARD,
        },
        {
            content: "The import is announced, naming the account",
            trigger: `${IMPORT}:contains('Notices account')`,
        },
        {
            content: "And nothing says the credentials expired",
            trigger: `${PANEL}:not(:has(.alert-warning))`,
        },
    ],
});

/**
 * Run the full resync cron, as the scheduler would, while the dashboard is
 * open: the page is not reloaded, so whatever the card shows afterwards
 * reached it through the bus.
 */
async function runFullResync() {
    const [cronId] = await rpc("/web/dataset/call_kw/ir.cron/search", {
        model: "ir.cron",
        method: "search",
        args: [[["code", "=", "model._run_full_resync()"]]],
        kwargs: {limit: 1},
    });
    await rpc("/web/dataset/call_kw/ir.cron/method_direct_trigger", {
        model: "ir.cron",
        method: "method_direct_trigger",
        args: [[cronId]],
        kwargs: {},
    });
}

/**
 * A check finds publications to import while the dashboard is open, and the
 * import brings them in later: the notice goes up and comes down on its own,
 * without the user reloading the page.
 */
registry
    .category("web_tour.tours")
    .add("social_media_sync.account_notices_import_live", {
        url: "/web#action=social_media_base.social_post_account_action",
        steps: () => [
            {
                content: "The card of the account is drawn",
                trigger: CARD,
            },
            {
                content: "Nothing is announced before the check runs",
                trigger: `${PANEL}:not(:has(.alert-info))`,
            },
            {
                content: "A check finds publications to import",
                trigger: CARD,
                run: runFullResync,
            },
            {
                content: "The import is announced, naming the account",
                trigger: `${IMPORT}:contains('Notices account')`,
            },
            {
                content: "The import brings them in",
                trigger: IMPORT,
                run: runFullResync,
            },
            {
                content: "And the notice comes down",
                trigger: `${PANEL}:not(:has(.alert-info))`,
            },
        ],
    });

/**
 * Both at once: neither state implies the other, so the card says the two
 * things it has to say instead of choosing one.
 */
registry.category("web_tour.tours").add("social_media_sync.account_notices_both", {
    url: "/web#action=social_media_base.social_post_account_action",
    steps: () => [
        {
            content: "The card of the account is drawn",
            trigger: CARD,
        },
        {
            content: "The credentials are announced",
            trigger: CREDENTIALS,
        },
        {
            content: "And so is the import, with its own text",
            trigger: IMPORT,
        },
    ],
});

/**
 * The steps of a tour that presses *Update* and waits for its notice.
 *
 * @param {String} notice the text the notification has to carry.
 * @returns {Function} the steps of the tour.
 */
function updateSteps(notice) {
    return () => [
        {
            content: "The card of the account is drawn",
            trigger: CARD,
        },
        {
            content: "The user asks for an update",
            trigger: "button.o_kanban_statistics_refresh_now",
            run: "click",
        },
        {
            content: "And is told what the update brought",
            trigger: `.o_notification .o_notification_content:contains('${notice}')`,
        },
    ];
}

/**
 * The *Update* button when the import read the account and brought
 * publications in: the notice says so, without saying how many.
 */
registry
    .category("web_tour.tours")
    .add("social_media_sync.update_with_new_publications", {
        url: "/web#action=social_media_base.social_post_account_action",
        steps: updateSteps("The data was updated. New publications were imported."),
    });

/**
 * The *Update* button when the import read the account and found nothing new.
 * Announcing publications it did not bring in is what would make the button
 * look broken the next time an account really is behind.
 */
registry
    .category("web_tour.tours")
    .add("social_media_sync.update_without_new_publications", {
        url: "/web#action=social_media_base.social_post_account_action",
        steps: updateSteps("The data was updated. No new publications."),
    });

/**
 * The *Update* button when no account was left to import: only the figures
 * moved, and the notice is the one base words from them.
 */
registry.category("web_tour.tours").add("social_media_sync.update_without_import", {
    url: "/web#action=social_media_base.social_post_account_action",
    steps: updateSteps("The data was updated successfully."),
});

/** Neither: an account nothing is pending on carries no notice at all. */
registry.category("web_tour.tours").add("social_media_sync.account_notices_none", {
    url: "/web#action=social_media_base.social_post_account_action",
    steps: () => [
        {
            content: "The card of the account is drawn",
            trigger: CARD,
        },
        {
            content: "And the dashboard announces nothing about it",
            trigger: `${PANEL}:not(:has(.alert-warning)):not(:has(.alert-info))`,
        },
    ],
});
