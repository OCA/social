/** @odoo-module **/

import {ThreadService} from "@mail/core/common/thread_service";
import {patch} from "@web/core/utils/patch";

patch(ThreadService.prototype, {
    /**
     * Carry the comment being replied to down to the backend.
     *
     * The thread controller hands `post_data` over untouched to
     * `create_comment`, so the target of the reply travels inside it and
     * neither the route nor the signature of the controller has to change.
     * Without a reply target the parameters are the ones `mail` builds, and
     * the comment is published on the post as it always was.
     *
     * @param {Object} params Parameters `mail` builds the message post with.
     * @returns {Promise<Object>} Those parameters, with the reply target added.
     */
    async getMessagePostParams(params) {
        const messagePostParams = await super.getMessagePostParams(params);
        const replyTarget = this.env.services.social_service?.replyTarget;
        if (params.thread?.model === "social.post.account" && replyTarget) {
            messagePostParams.post_data.social_parent_ref = replyTarget.commentRef;
        }
        return messagePostParams;
    },
});
