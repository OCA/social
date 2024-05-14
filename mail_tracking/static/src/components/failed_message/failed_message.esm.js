/** @odoo-module **/
import {AvatarCardPopover} from "@mail/discuss/web/avatar_card/avatar_card_popover";
import {FailedMessageReview} from "@mail_tracking/components/failed_message_review/failed_message_review.esm";
import {MessageTracking} from "@mail_tracking/components/message_tracking/message_tracking.esm";
import {RelativeTime} from "@mail/core/common/relative_time";
import {url} from "@web/core/utils/urls";
import {usePopover} from "@web/core/popover/popover_hook";
import {useService} from "@web/core/utils/hooks";

const {Component, useState} = owl;

export class FailedMessage extends Component {
    static props = ["message", "onUpdate?", "reloadParentView"];
    // eslint-disable-next-line no-empty-function
    static defaultProps = {onUpdate: () => {}};
    static template = "mail_tracking.FailedMessage";
    static components = {
        RelativeTime,
        MessageTracking,
        FailedMessageReview,
    };

    setup() {
        this.avatarCard = usePopover(AvatarCardPopover);
        this.threadService = useState(useService("mail.thread"));
        this.state = useState({showDetails: false});
        this.message = useState(this.props.message);
        this.orm = useService("orm");
    }
    async setFailedMessageReviewed() {
        await this.orm.call("mail.message", "set_need_action_done", [
            [this.message.id],
        ]);
        // Debugger
        const thread = this.env.services["mail.thread"].getThread(
            this.message.model,
            this.message.id
        );
        this.env.services["mail.thread"].fetchNewMessages(thread);
        this.props.reloadParentView();
    }
    retryFailedMessage() {
        this.env.services.action.doAction("mail.mail_resend_message_action", {
            additionalContext: {
                mail_message_to_resend: this.message.id,
            },
            onClose: async () => {
                // Check if message is still 'failed' after Retry
                await this.orm.call("mail.message", "get_failed_messages", [
                    [this.message.id],
                ]);
            },
        });
    }
    async onClickJump() {
        await this.env.messageHighlight?.highlightMessage(
            this.message,
            this.message.originThread
        );
    }
    toggleDetails() {
        this.state.showDetails = !this.state.showDetails;
    }
    hasAuthorClickable() {
        return this.message.author?.user;
    }
    onClickAvatar(ev) {
        if (this.hasAuthorClickable()) {
            const target = ev.currentTarget;
            if (!this.avatarCard.isOpen) {
                this.avatarCard.open(target, {
                    id: this.message.author.user.id,
                });
            }
        }
    }
    get authorAvatarAttClass() {
        return {
            o_object_fit_contain: this.props.message.author?.is_company,
            o_object_fit_cover: !this.props.message.author?.is_company,
            "cursor-pointer": this.hasAuthorClickable() || "initial",
        };
    }
    get authorAvatarUrl() {
        if (
            this.message.type &&
            this.message.type.includes("email") &&
            !["partner", "guest"].includes(this.message.author?.type)
        ) {
            return url("/mail/static/src/img/email_icon.png");
        }
        return this.threadService.avatarUrl(
            this.message.author,
            this.message.originThread
        );
    }
    get thread() {
        return this.threadService.getThread(
            this.message.res_model,
            this.message.res_id
        );
    }
    get failed_recipients() {
        const error_states = ["error", "rejected", "spam", "bounced", "soft-bounced"];
        return this.message.partner_trackings.filter((message) => {
            return error_states.includes(message.status);
        });
    }
}
