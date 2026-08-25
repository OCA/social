/** @odoo-module **/
import {SocialKanbanRecord} from "@social_media_base/js/views/kanban/social_kanban_record.esm";
import {patch} from "@web/core/utils/patch";

patch(SocialKanbanRecord.prototype, {
    /** @override */
    setup() {
        super.setup();
        this.record.notAvailableLike = [...(this.record.notAvailableLike || []), "x"];
    },
});
