import {Message} from "@mail/core/common/message";
import {patch} from "@web/core/utils/patch";
import {url} from "@web/core/utils/urls";

patch(Message.prototype, {
    get authorAvatarUrl() {
        if (
            this.message.gateway_type &&
            this.message.gateway_type.includes("whatsapp") &&
            !["partner", "guest"].includes(this.message.author?.type)
        ) {
            return url("/mail_gateway_whatsapp/static/description/icon.png");
        }
        return super.authorAvatarUrl;
    },
});
