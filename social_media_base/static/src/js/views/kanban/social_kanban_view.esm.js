import {SocialKanbanController} from "./social_kanban_controller.esm";
import {SocialKanbanModel} from "./social_kanban_model.esm";
import {SocialKanbanRenderer} from "./social_kanban_renderer.esm";
import {kanbanView} from "@web/views/kanban/kanban_view";
import {registry} from "@web/core/registry";

export const SocialKanbanView = {
    ...kanbanView,
    Controller: SocialKanbanController,
    Model: SocialKanbanModel,
    Renderer: SocialKanbanRenderer,
    buttonTemplate: "SocialKanbanView.buttons",
};

registry.category("views").add("social_kanban", SocialKanbanView);
