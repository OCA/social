import {SocialComment} from "@social_media_base/components/social_comment/social_comment.esm";
import {patch} from "@web/core/utils/patch";
import {useService} from "@web/core/utils/hooks";

patch(SocialComment.prototype, {
    /**
     * Sets up the component's services.
     *
     * This method is called once, when the component is set up.
     * It sets up the component's services and initializes its state.
     * It also fetches the `socialLinkedinService` service that provides
     * the logic for deleting comments on LinkedIn.
     */
    setup() {
        super.setup();
        this.socialLinkedinService = useService("social_linkedin_service");
    },
    /**
     * Deletes a LinkedIn comment.
     *
     * This method calls the `deleteLinkedinComment` method from the
     * `socialLinkedinService` to delete the comment associated with the
     * provided post and comment IDs, as well as the actor. It overrides
     * the base implementation to provide LinkedIn-specific deletion logic.
     *
     * @returns {Object}
     *   An object containing a `success` property indicating whether the
     *   deletion was successful, and a `message` property with the result
     *   message.
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
     * Returns the list of media types for which liking a comment is not
     * supported.
     *
     * This method overrides the base implementation to add LinkedIn to the
     * list of media types for which liking a comment is not supported.
     *
     * @returns {String[]}
     *   An array of strings, where each string is a media type.
     */
    mediaNotLikeEnable() {
        const values = super.mediaNotLikeEnable();
        values.push("linkedin");
        return values;
    },
});
