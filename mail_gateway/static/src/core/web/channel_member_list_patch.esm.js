import {ChannelMemberList} from "@mail/discuss/core/common/channel_member_list";
import {patch} from "@web/core/utils/patch";

patch(ChannelMemberList.prototype, {
    onClickAvatar(ev, member) {
        if (!this.canOpenChatWith(member)) {
            return;
        }
        if (!this.avatarCard.isOpen && member.partner_id.main_user_id?.id) {
            this.avatarCard.open(ev.currentTarget, {
                id: member.partner_id.main_user_id.id,
            });
        }
    },
});
