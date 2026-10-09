/* @odoo-module */

import {DiscussCoreCommon} from "@mail/discuss/core/common/discuss_core_common_service";

import {patch} from "@web/core/utils/patch";

patch(DiscussCoreCommon.prototype, {
    async _handleNotificationNewMessage(notif) {
        await super._handleNotificationNewMessage(notif);
        const channel = this.store.Thread.get({
            id: notif.payload.id,
            model: "discuss.channel",
        });
        if (channel && channel.selfMember) {
            channel.is_pinned = true;
            channel.selfMember.is_sidebar_hidden = false;
        }
    },
});
