import "@mail/chatter/web/mail_composer_send_dropdown"; // <- side-effect
import {registry} from "@web/core/registry";
import {patch} from "@web/core/utils/patch";

const def = registry.category("view_widgets").get("mail_composer_send_dropdown");
const MailComposerSendDropdownClass = def.component;

patch(MailComposerSendDropdownClass.prototype, {
    async onClickSend() {
        const model = this.env.model.config.resModel;
        if (model === "mail.compose.message") {
            return await super.onClickSend(...arguments);
        }
        this.buttonState.disabled = true;
        if (await this.props.record.save()) {
            const method = this.props.record.data.scheduled_date
                ? "action_schedule_message"
                : "action_send_mail";
            this.actionService.doAction(
                await this.orm.call(model, method, [this.props.record.resId], {
                    context: this.props.record.context,
                })
            );
        }
        this.buttonState.disabled = false;
    },
});
