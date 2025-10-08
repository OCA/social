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
        this.socialXService = useService("social_x_service");
        this.record.notAvailableLike += ["x"];
    },
    async validPostExist() {
        const res = super.validPostExist();
        if (this.record.media_type.raw_value === "x") {
            return await this.socialXService.validPostXExist(this.record.id.raw_value);
        }
        return res;
    },
});
