/** @odoo-module **/

import {SocialKanbanRecord} from "@social_media_base/js/views/kanban/social_kanban_record.esm";
import {patch} from "@web/core/utils/patch";

/**
 * What this bridge serves on a publication of X: the import writes its
 * figures and the thread is answered by `social.post.account` here, but the
 * reaction is not, so the card draws everything but the *Recommend* entry.
 */
patch(SocialKanbanRecord.prototype, {
    /** @override */
    setup() {
        super.setup();
        const capabilities = this.record.syncCapabilities;
        capabilities.statistics.push("x");
        capabilities.comments.push("x");
    },
});
