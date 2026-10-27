/** @odoo-module */

import {registry} from "@web/core/registry";

const CARD = ".o_kanban_record:contains('X tour publication')";
const ENTRY = `${CARD} .social-like-post`;
const THREAD = ".o_social_comment_thread";
const OWN = `${THREAD} > .o_social_comment:contains('Own comment')`;
const LIKED = `${THREAD} > .o_social_comment:contains('Liked comment')`;
const PLAIN = `${THREAD} > .o_social_comment:contains('Plain comment')`;
const REPLIES = `${PLAIN} .o_social_comment_replies`;
const LIKED_REPLY = `${REPLIES} > .o_social_comment:contains('Liked reply')`;
const PLAIN_REPLY = `${REPLIES} > .o_social_comment:contains('Plain reply')`;
const MENU = ".o-mail-Message-header .fa-ellipsis-v";
const LIKE = ".o_social_comment_actions button[title^='Recommend this comment']";
const TOGGLE = ".o_social_comment_actions button[title^='Show or hide the replies']";

/**
 * What the card of a publication of X offers: the figures, the reaction and
 * the thread. This bridge imports the first and answers the other two.
 *
 * @returns {Object[]} the steps of the tour.
 */
const cardFooterSteps = () => [
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
        content: "The reaction is offered: this bridge answers it",
        trigger: ENTRY,
        isCheck: true,
    },
];

/**
 * What pressing the like of the card sends to X. The entry is a toggle, and
 * each half of it reaches X once.
 *
 * @returns {Object[]} the steps of the tour.
 */
const postReactionSteps = () => [
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
];

/**
 * What the dialog of the publication offers on each comment, and what a
 * reload of the comments, which arrives without the likes, leaves of them.
 *
 * The replies are what tells the like kept from the like lost: a comment on
 * screen keeps its component across the reload, while a branch unfolded
 * after it draws its replies anew from the list the dialog holds.
 *
 * @returns {Object[]} the steps of the tour.
 */
const commentDialogSteps = () => [
    {
        content: "Open the thread of the publication",
        trigger: `${CARD} .social-post-comment`,
        run: "click",
    },
    {
        content: "The comment of the account offers its deletion",
        trigger: `${OWN} ${MENU}`,
        isCheck: true,
    },
    {
        content: "A comment of somebody else does not",
        trigger: `${LIKED}:not(:has(${MENU}))`,
        isCheck: true,
    },
    {
        content: "The comment the account liked on X is drawn liked",
        trigger: `${LIKED} ${LIKE} .fa-thumbs-up`,
        isCheck: true,
    },
    {
        content: "The one it did not like is drawn without it",
        trigger: `${PLAIN} > div ${LIKE} .fa-thumbs-o-up`,
        isCheck: true,
    },
    {
        content: "Like it from the dialog",
        trigger: `${PLAIN} > div ${LIKE}:first`,
        run: "click",
    },
    {
        content: "It is drawn liked",
        trigger: `${PLAIN} > div ${LIKE}:first .fa-thumbs-up`,
        isCheck: true,
    },
    {
        content: "Unfold its replies",
        trigger: `${PLAIN} ${TOGGLE}`,
        run: "click",
    },
    {
        content: "The reply the account liked on X is drawn liked",
        trigger: `${LIKED_REPLY} ${LIKE} .fa-thumbs-up`,
        isCheck: true,
    },
    {
        content: "Like the other reply from the dialog",
        trigger: `${PLAIN_REPLY} ${LIKE}`,
        run: "click",
    },
    {
        content: "It is drawn liked",
        trigger: `${PLAIN_REPLY} ${LIKE} .fa-thumbs-up`,
        isCheck: true,
    },
    {
        content: "Fold the replies again",
        trigger: `${PLAIN} ${TOGGLE}`,
        run: "click",
    },
    {
        content: "The branch is folded",
        trigger: `${PLAIN}:not(:has(.o_social_comment_replies))`,
        isCheck: true,
    },
    {
        content: "Open the menu of the comment of the account",
        trigger: `${OWN} ${MENU}`,
        run: "click",
    },
    {
        content: "Delete it",
        trigger: ".dropdown-item:contains('Delete')",
        run: "click",
    },
    {
        content: "Confirm the deletion, which reloads the comments",
        trigger: ".modal-footer .btn-primary:contains('Delete')",
        run: "click",
    },
    {
        content: "The deleted comment is gone after the reload",
        trigger: `${THREAD}:not(:has(.o_social_comment:contains('Own comment')))`,
        isCheck: true,
    },
    {
        content: "Unfold the replies, drawn anew from the reloaded list",
        trigger: `${PLAIN} ${TOGGLE}`,
        run: "click",
    },
    {
        content: "The like read when the dialog opened is kept",
        trigger: `${LIKED_REPLY} ${LIKE} .fa-thumbs-up`,
        isCheck: true,
    },
    {
        content: "And so is the like given from the dialog",
        trigger: `${PLAIN_REPLY} ${LIKE} .fa-thumbs-up`,
        isCheck: true,
    },
    {
        content: "The comments on screen keep theirs too",
        trigger: `${LIKED} ${LIKE} .fa-thumbs-up`,
        isCheck: true,
    },
];

/**
 * The dashboard of X walked in a single tour: every tour opens its own
 * browser, and closing it is what costs the most time in a test run.
 */
registry.category("web_tour.tours").add("social_media_x_sync.dashboard", {
    test: true,
    url: "/web#action=social_media_base.social_post_account_action",
    steps: () => [
        ...cardFooterSteps(),
        ...postReactionSteps(),
        ...commentDialogSteps(),
    ],
});
