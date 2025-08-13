import {Message} from "@mail/core/common/message";
import {_t} from "@web/core/l10n/translation";
import {patch} from "@web/core/utils/patch";

patch(Message.prototype, {
    hasAuthorClickable() {
        if (
            this.message.gateway_type &&
            this.message.author?.type === "guest" &&
            this.message.author.id
        ) {
            return true;
        }
        return super.hasAuthorClickable();
    },
    getAuthorText() {
        if (this.hasAuthorClickable() && this.message.gateway_type) {
            return _t("Create partner");
        }
        return super.getAuthorText();
    },
    onClickAuthor(ev) {
        if (this.message.gateway_type && this.hasAuthorClickable()) {
            ev.stopPropagation();
            return this.env.services.action.doAction({
                name: _t("Manage guest"),
                type: "ir.actions.act_window",
                res_model: "mail.guest.manage",
                context: {default_guest_id: this.message.author.id},
                views: [[false, "form"]],
                target: "new",
            });
        }
        return super.onClickAuthor(...arguments);
    },
    onClickLinkGatewayToThread() {
        this.env.services.action.doAction({
            name: _t("Link Message to thread"),
            type: "ir.actions.act_window",
            res_model: "mail.message.gateway.link",
            context: {default_message_id: this.message.id},
            views: [[false, "form"]],
            target: "new",
        });
    },
    onClickSendWithGateway() {
        this.env.services.action.doAction({
            name: _t("Send with gateway"),
            type: "ir.actions.act_window",
            res_model: "mail.message.gateway.send",
            context: {
                ...this.props.message.gateway_channel_data,
                default_message_id: this.props.message.id,
            },
            views: [[false, "form"]],
            target: "new",
        });
    },
    openGatewayThreadRecord() {
        this.store.env.services.action.doAction({
            type: "ir.actions.act_window",
            res_id: this.message.gateway_thread_data.id,
            res_model: this.message.gateway_thread_data.model,
            views: [[false, "form"]],
        });
    },
});
