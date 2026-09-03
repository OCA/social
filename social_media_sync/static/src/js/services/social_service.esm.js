/** @odoo-module */

import {_t} from "@web/core/l10n/translation";
import {reactive} from "@odoo/owl";
import {registry} from "@web/core/registry";

export const socialService = {
    dependencies: ["orm"],

    async start(env, {orm}) {
        // The comment being replied to is shared state: the button that sets
        // it lives in one component and the banner that shows it in another.
        // It is reactive so both of them redraw, and a component that needs
        // to follow it subscribes with `useState(socialService.state)`.
        const state = reactive({replyTarget: null});
        return {
            state,
            get replyTarget() {
                return state.replyTarget;
            },
            setReplyTarget(commentRef, actorLabel) {
                state.replyTarget = {commentRef, actorLabel};
            },
            clearReplyTarget() {
                state.replyTarget = null;
            },
            /**
             * Aim at a comment, or disarm when it is already the aimed one.
             *
             * This is the arm/disarm of `mail`, whose reply target is
             * cancelled by clicking the same message again
             * (`@mail/utils/common/hooks` useMessageToReplyTo.toggle). A
             * comment is not a `mail.message`, so what is compared is the
             * reference of the social media instead of the record.
             *
             * @param {String} commentRef Reference of the aimed comment.
             * @param {String} actorLabel Who wrote it, as the media says it.
             */
            toggleReplyTarget(commentRef, actorLabel) {
                if (state.replyTarget?.commentRef === commentRef) {
                    state.replyTarget = null;
                    return;
                }
                state.replyTarget = {commentRef, actorLabel};
            },
            async getComments(postAccountId = null) {
                if (!postAccountId) {
                    return [];
                }
                return await orm.call("social.post.account", "get_comments", [
                    postAccountId,
                ]);
            },
            async getCommentReplies(postAccountId, commentRef) {
                if (!postAccountId || !commentRef) {
                    return {success: false, data: [], count: 0};
                }
                return await orm.call("social.post.account", "get_comment_replies", [
                    [postAccountId],
                    commentRef,
                ]);
            },
            async likeComment(postAccountId, commentRef, actorUrn) {
                if (!postAccountId || !commentRef || !actorUrn) {
                    return {
                        success: false,
                        message: _t("An error occurred while liking the comment"),
                    };
                }
                return await orm.call("social.post.account", "action_like_comment", [
                    [postAccountId],
                    commentRef,
                    actorUrn,
                ]);
            },
        };
    },
};

registry.category("services").add("social_service", socialService);
