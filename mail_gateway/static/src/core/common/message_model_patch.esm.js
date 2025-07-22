/* @odoo-module */
import {Message} from "@mail/core/common/message_model";
import {patch} from "@web/core/utils/patch";
import {url} from "@web/core/utils/urls";

patch(Message, {
    get resUrl() {
        if (!this.gateway_thread_data) {
            return super.resUrl;
        }
        return `${url("/web")}#model=${this.gateway_thread_data.model}&id=${
            this.gateway_thread_data.id
        }`;
    },
});

patch(Message.prototype, {
    get editable() {
        return super.editable && !this.gateway_type;
    },
});
