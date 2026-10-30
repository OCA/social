import {useService} from "@web/core/utils/hooks";
import {_t} from "@web/core/l10n/translation";
import {user} from "@web/core/user";
import {Component, status} from "@odoo/owl";

export class SendWhatsappButton extends Component {
    setup() {
        this.action = useService("action");
        this.title = _t("Send Whatsapp Message");
    }
    get phoneHref() {
        return "sms:" + this.props.record.data[this.props.name].replace(/\s+/g, "");
    }
    async onClick() {
        await this.props.record.save();
        this.action.doAction(
            {
                type: "ir.actions.act_window",
                target: "new",
                name: this.title,
                res_model: "whatsapp.composer",
                views: [[false, "form"]],
                context: {
                    ...user.context,
                    default_res_model: this.props.record.resModel,
                    default_res_id: this.props.record.resId,
                    default_number_field_name: this.props.name,
                    default_composition_mode: "comment",
                },
            },
            {
                onClose: () => {
                    if (status(this) !== "destroyed") {
                        this.props.record.load();
                        this.props.record.model.notify();
                    }
                },
            }
        );
    }
}
SendWhatsappButton.template = "mail_gateway_whatsapp.SendWhatsappButton";
