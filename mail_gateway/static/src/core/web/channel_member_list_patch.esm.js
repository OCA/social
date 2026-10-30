import {ChannelMemberList} from "@mail/discuss/core/common/channel_member_list";
import {patch} from "@web/core/utils/patch";

patch(ChannelMemberList.prototype, {
    onClickAvatar(ev, member) {
        if (!this.canOpenChatWith(member)) {
            return;
        }
        if (!this.avatarCard.isOpen && member.persona.userId) {
            this.avatarCard.open(ev.currentTarget, {
                id: member.persona.userId,
            });
        }
    },
});
