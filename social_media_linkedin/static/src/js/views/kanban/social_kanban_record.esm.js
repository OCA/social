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
        this.socialLinkedinService = useService("social_linkedin_service");
    },

    /**
     * Checks on LinkedIn whether the post still exists.
     *
     * @override
     * @returns {Promise<Boolean>} Whether the post exists
     */
    async validPostExist() {
        var res = super.validPostExist();
        if (this.record.media_type.raw_value === "linkedin") {
            return await this.socialLinkedinService.validPostLinkedinExist(
                this.record.id.raw_value
            );
        }
        return res;
    },
});
