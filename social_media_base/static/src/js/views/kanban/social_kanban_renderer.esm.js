/** @odoo-module **/

import {KanbanRenderer} from "@web/views/kanban/kanban_renderer";
import {SocialKanbanRecord} from "./social_kanban_record.esm";
import {SocialMediaMixin} from "../../app/social_media_mixin.esm";
import {useService} from "@web/core/utils/hooks";

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
};
