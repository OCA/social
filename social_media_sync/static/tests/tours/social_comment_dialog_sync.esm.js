/** @odoo-module */

import {registry} from "@web/core/registry";

const CARD = ".o_kanban_record:contains('Conversation publication')";
// Once the dialog is open the triggers are looked up inside it, so they are
// written relative to the modal and not from the document.
const THREAD = ".o_social_comment_thread";
// The roots are the direct children of the thread: a reply is drawn inside
// the block of the comment it hangs from.
const ROOT = `${THREAD} > .o_social_comment`;
const REPLIES = `${ROOT}:nth-child(1) .o_social_comment_replies`;

/**
 * The conversation is drawn as the social media answered it: the roots in
 * the order they arrived, and under each of them its replies in theirs. A
 * reply of a reply hangs from the comment that started the branch, and a
 * ``parent_ref`` closing on itself is drawn instead of hanging the dialog.
 */
registry.category("web_tour.tours").add("social_media_sync.comment_dialog", {
    test: true,
    url: "/web#action=social_media_base.social_post_account_action",
    steps: () => [
        {
            content: "Open the thread of the publication",
            trigger: `${CARD} .social-post-comment`,
            run: "click",
        },
        {
            content: "The first root is the first comment answered",
            trigger: `${ROOT}:nth-child(1):contains('Root one')`,
            isCheck: true,
        },
        {
            content: "The second root comes after it",
            trigger: `${ROOT}:nth-child(2):contains('Root two')`,
            isCheck: true,
        },
        {
            content: "The pair pointing at each other is drawn, in its order",
            trigger: `${ROOT}:nth-child(3):contains('Cycle A')`,
            isCheck: true,
        },
        {
            content: "And the dialog is still answering, so nothing looped",
            trigger: `${ROOT}:nth-child(4):contains('Cycle B')`,
            isCheck: true,
        },
        {
            content: "Four roots and no more",
            trigger: `${THREAD}:not(:has(> .o_social_comment:nth-child(5)))`,
            isCheck: true,
        },
        {
            content: "Unfold the branch of the first root",
            trigger: `${ROOT}:nth-child(1) button:contains('View replies')`,
            run: "click",
        },
        {
            content: "Its reply is drawn first",
            trigger: `${REPLIES} > .o_social_comment:nth-child(1):contains('Reply to one')`,
            isCheck: true,
        },
        {
            content: "And the reply of that reply hangs from the same root",
            trigger: `${REPLIES} > .o_social_comment:nth-child(2):contains('Reply of the reply')`,
            isCheck: true,
        },
        {
            content: "Two replies in the branch and no more",
            trigger: `${REPLIES}:not(:has(> .o_social_comment:nth-child(3)))`,
            isCheck: true,
        },
    ],
});
