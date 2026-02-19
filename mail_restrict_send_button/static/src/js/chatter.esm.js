import {Chatter} from "@mail/chatter/web_portal/chatter";
import {onWillStart} from "@odoo/owl";
import {patch} from "@web/core/utils/patch";
import {user} from "@web/core/user";

patch(Chatter.prototype, {
    setup() {
        super.setup(...arguments);
        onWillStart(async () => {
            this.isSendMessage = await user.hasGroup(
                "mail_restrict_send_button.group_show_send_message_button"
            );
        });
    },
});
