/** @odoo-module **/

import {SocialComment} from "@social_media_base/components/social_comment/social_comment.esm";
import {patch} from "@web/core/utils/patch";
import {useService} from "@web/core/utils/hooks";

patch(SocialComment.prototype, {
    /**
     * @override
     */
    setup() {
        super.setup();
        this.socialLinkedinService = useService("social_linkedin_service");
    },
    /**
     * Deletes the comment on LinkedIn.
     *
     * @override
     * @returns {Object} With `success` and `message`
     */
    async _onDeleteComment() {
        let result = super._onDeleteComment();
        result = await this.socialLinkedinService.deleteLinkedinComment(
            this.props.post.id.raw_value,
            this.props.socialComment.id,
            this.props.socialComment.actor
        );
        return result;
    },

    /**
     * Adds LinkedIn, which does not support liking a comment.
     *
     * @override
     * @returns {String[]} The media types without comment like
     */
    mediaNotLikeEnable() {
        const values = super.mediaNotLikeEnable();
        values.push("linkedin");
        return values;
    },
});
