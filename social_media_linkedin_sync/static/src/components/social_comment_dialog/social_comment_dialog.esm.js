/** @odoo-module **/

import {SocialCommentDialog} from "@social_media_sync/components/social_comment_dialog/social_comment_dialog.esm";
import {patch} from "@web/core/utils/patch";

patch(SocialCommentDialog.prototype, {
    /**
     * LinkedIn takes no image on a comment.
     *
     * @override
     */
    get commentAllowUpload() {
        if (this.props.media_type.raw_value === "linkedin") {
            return false;
        }
        return super.commentAllowUpload;
    },
});
