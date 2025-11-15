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
     * Checks if the post exists.
     *
     * This function returns a boolean indicating whether the post exists.
     * It calls the "validPostLinkedinExist" method on the "social_linkedin_service",
     * passing the `id` field of the record as an argument.
     *
     * @returns {Promise<Boolean>} a promise that resolves with `true` if the post exists,
     * otherwise `false`.
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
