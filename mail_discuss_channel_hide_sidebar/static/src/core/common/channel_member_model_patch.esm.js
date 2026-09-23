/* @odoo-module */

import {ChannelMember} from "@mail/core/common/channel_member_model";
import {Record} from "@mail/core/common/record";

import {patch} from "@web/core/utils/patch";

patch(ChannelMember.prototype, {
    is_sidebar_hidden: Record.attr(false),
});
