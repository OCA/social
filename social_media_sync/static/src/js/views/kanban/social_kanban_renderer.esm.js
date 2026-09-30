/** @odoo-module **/

import {SocialKanbanRenderer} from "@social_media_base/js/views/kanban/social_kanban_renderer.esm";
import {patch} from "@web/core/utils/patch";

/**
 * The dashboard also listens for the publications waiting to be imported.
 *
 * Its own bus type, and not the one the expired credentials use: neither
 * state implies the other, and an account can be announcing both at once.
 * Base is not taught the new type on purpose — the field, the notice and the
 * message are this module's.
 */
patch(SocialKanbanRenderer.prototype, {
    /** @override */
    handleSocialViewNotification(type, payload) {
        super.handleSocialViewNotification(type, payload);
        if (!payload) {
            return;
        }
        if (type === "social_posts_need_import") {
            // The server also broadcasts the notice coming down, so the flag
            // cannot be hardcoded here: the import that brings the
            // publications in has to clear the notice without the user
            // reloading the page.
            this.env.bus.trigger("SOCIAL:POSTS-NEED-IMPORT", {
                needUpdate: payload.need_update ?? true,
                accounts: payload.accounts ?? [],
            });
        }
    },
});
