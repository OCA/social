import {Composer} from "@mail/core/common/composer";
import {_t} from "@web/core/l10n/translation";
import {patch} from "@web/core/utils/patch";
import {prettifyMessageContent} from "@mail/utils/common/format";

patch(Composer.prototype, {
    get SEND_TEXT() {
        if (this.props.type === "gateway" && !this.props.composer.message) {
            return _t("Send gateway");
        }
        return super.SEND_TEXT;
    },
    get placeholder() {
        if (
            this.thread?.model !== "discuss.channel" &&
            !this.props.placeholder &&
            this.props.type === "gateway"
        ) {
            return _t("Send a message to a gateway...");
        }
        return super.placeholder;
    },
    get isSendButtonDisabled() {
        const isSendButtonDisabled = super.isSendButtonDisabled;
        if (this.props.type !== "gateway") {
            return isSendButtonDisabled;
        }
        return isSendButtonDisabled || !this.thread?.gateway_notifications?.length;
    },
    onFocusin() {
        super.onFocusin();
        if (this.props.type !== "gateway" && this.thread) {
            this.thread.gateway_notifications = [];
        }
    },
    async onClickFullComposer() {
        if (this.props.type !== "gateway") {
            return super.onClickFullComposer(...arguments);
        }
        const attachmentIds = this.props.composer.attachments.map(
            (attachment) => attachment.id
        );
        const body = this.props.composer.textInputContent;
        const validMentions = this.store.user
            ? this.messageService.getMentionsFromText(body, {
                  mentionedChannels: this.props.composer.mentionedChannels,
                  mentionedPartners: this.props.composer.mentionedPartners,
              })
            : undefined;
        // Debugger
        const context = {
            default_attachment_ids: attachmentIds,
            default_body: await prettifyMessageContent(body, validMentions),
            default_model: this.thread.model,
            default_partner_ids: this.thread.suggestedRecipients
                .filter((recipient) => recipient.checked)
                .map((recipient) => recipient.persona.id),
            default_res_ids: [this.thread.id],
            default_subtype_xmlid: "mail.mt_comment",
            mail_post_autofollow: this.thread.hasWriteAccess,
            default_wizard_partner_ids: Array.from(
                new Set(
                    this.thread.gateway_followers.map((follower) => {
                        return follower.id;
                    })
                )
            ),
            default_wizard_channel_ids: Array.from(
                new Set(
                    this.thread.gateway_followers
                        .map((follower) => {
                            return follower.gateway_channels.map(
                                (channel) => channel?.id
                            );
                        })
                        .flat()
                )
            ),
        };
        const action = {
            name: _t("Gateway message"),
            type: "ir.actions.act_window",
            res_model: "mail.compose.gateway.message",
            view_mode: "form",
            views: [[false, "form"]],
            target: "new",
            context: context,
        };
        const options = {
            onClose: (...args) => {
                // Args === [] : click on 'X'
                // args === { special: true } : click on 'discard'
                const isDiscard = args.length === 0 || args[0]?.special;
                // Otherwise message is posted (args === [undefined])
                if (!isDiscard && this.props.composer.thread.type === "mailbox") {
                    this.notifySendFromMailbox();
                }
                this.clear();
                this.props.messageToReplyTo?.cancel();
                if (this.thread) {
                    this.thread?.fetchNewMessages();
                }
            },
        };
        await this.env.services.action.doAction(action, options);
    },
});
