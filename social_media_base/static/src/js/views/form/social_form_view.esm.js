/** @odoo-module **/

import {SocialFormRenderer} from "./social_form_renderer.esm";
import {formView} from "@web/views/form/form_view";
import {registry} from "@web/core/registry";

export const SocialFormView = {
    ...formView,
    Renderer: SocialFormRenderer,
};

registry.category("views").add("social_form", SocialFormView);
