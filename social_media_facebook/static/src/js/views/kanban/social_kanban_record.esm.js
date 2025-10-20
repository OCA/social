/** @odoo-module **/
import {SocialKanbanRecord} from "@social_media_base/js/views/kanban/social_kanban_record.esm";
import {patch} from "@web/core/utils/patch";
import {useService} from "@web/core/utils/hooks";

patch(SocialKanbanRecord.prototype, {
    /**
     * @override
     */
    setup() {
        super.setup();
        this.socialFacebookService = useService("social_facebook_service");
    },

    /**
     * Check if a Facebook post exists and is accessible.
     *
     * For Facebook, we check if the post has valid content and metrics.
     * This can be extended to verify post existence via API.
     *
     * @returns {Promise<Boolean>} true if the post exists and is valid
     */
    async validPostExist() {
        const res = super.validPostExist();
        if (this.record.media_type?.raw_value === "facebook") {
            // Facebook posts are considered valid if they have a content ID
            return Boolean(this.record.fb_content_id?.raw_value);
        }
        return res;
    },

    /**
     * Sync Facebook content for the current account.
     *
     * @returns {Promise<void>}
     */
    async syncFacebookContent() {
        if (this.record.media_type?.raw_value === "facebook") {
            await this.socialFacebookService.syncFacebookContent(
                this.record.id.raw_value
            );
        }
    },
});
