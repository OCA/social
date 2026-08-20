import {KanbanRenderer} from "@web/views/kanban/kanban_renderer";
import {KanbanHeader} from "@web/views/kanban/kanban_header";
import {SocialKanbanRecord} from "./social_kanban_record.esm";
import {SocialMediaMixin} from "../../app/social_media_mixin.esm";
import {useService} from "@web/core/utils/hooks";

export class SocialKanbanHeader extends KanbanHeader {
    static template = "social_media_base.KanbanHeader";

    /**
     * Get the image URL for the grouped field's avatar
     */
    get groupImageUrl() {
        const group = this.props.group;
        if (!group || !group.groupByField || group.groupByField.name !== "account_id") {
            return null;
        }
        // Get the account_id value
        const accountId = group.value;
        if (!accountId) {
            return null;
        }
        // For social.account grouped by account_id, show the media icon
        // The avatar_128 field is computed to return media_id.image
        return `/web/image/social.account/${accountId}/avatar_128`;
    }
}

export class SocialKanbanRenderer extends SocialMediaMixin(KanbanRenderer) {
    setup() {
        super.setup();
        this.notificationService = useService("notification");
        this.busService = this.env.services.bus_service;
        this.enableSocialNotifications();
    }
}

SocialKanbanRenderer.components = {
    ...KanbanRenderer.components,
    KanbanRecord: SocialKanbanRecord,
    KanbanHeader: SocialKanbanHeader,
};
