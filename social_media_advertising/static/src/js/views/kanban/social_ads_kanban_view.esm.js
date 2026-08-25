/** @odoo-module **/

import {SocialAdsKanbanController} from "./social_ads_kanban_controller.esm";
import {kanbanView} from "@web/views/kanban/kanban_view";
import {registry} from "@web/core/registry";

export const SocialAdsKanbanView = {
    ...kanbanView,
    Controller: SocialAdsKanbanController,
    buttonTemplate: "social_media_advertising.AdsKanbanView.Buttons",
};

registry.category("views").add("social_ads_kanban", SocialAdsKanbanView);
