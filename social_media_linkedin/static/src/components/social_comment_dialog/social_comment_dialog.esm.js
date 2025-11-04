import {SocialCommentDialog} from "@social_media_base/components/social_comment_dialog/social_comment_dialog.esm";
import {patch} from "@web/core/utils/patch";

patch(SocialCommentDialog.prototype, {
    _commentAllowUpload() {
        const result = super._commentAllowUpload();
        if (this.props.media_type.raw_value === "linkedin") {
            return false;
        }
        return result;
    },
});
