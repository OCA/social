/** @odoo-module **/

import {SocialKanbanRecord} from "@social_media_base/js/views/kanban/social_kanban_record.esm";
import {patch} from "@web/core/utils/patch";

/**
 * What this bridge serves on a publication of X: the import writes its
 * figures, and the reaction and the thread are answered by
 * `social.post.account` here, so the card draws the three halves of the
 * footer.
 */
patch(SocialKanbanRecord.prototype, {
    /** @override */
    setup() {
        super.setup();
        const capabilities = this.record.syncCapabilities;
        capabilities.statistics.push("x");
        capabilities.reactions.push("x");
        capabilities.comments.push("x");
    },
});
