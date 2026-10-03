/** @odoo-module **/

import {SocialKanbanRecord} from "@social_media_base/js/views/kanban/social_kanban_record.esm";
import {patch} from "@web/core/utils/patch";

/**
 * What this bridge serves on a publication of LinkedIn: the import writes its
 * figures, and the reaction and the thread are answered by
 * `social.post.account` here, so the card draws the three halves of the
 * footer. A publication of another social media keeps whatever its own bridge
 * declares.
 */
patch(SocialKanbanRecord.prototype, {
    /** @override */
    setup() {
        super.setup();
        const capabilities = this.record.syncCapabilities;
        capabilities.statistics.push("linkedin");
        capabilities.reactions.push("linkedin");
        capabilities.comments.push("linkedin");
    },
});
