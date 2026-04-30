/** @odoo-module **/

import { Composer } from "@mail/core/common/composer";
import { patch } from "@web/core/utils/patch";

patch(Composer.prototype, {
    get whatsappButton() {
        return this.props.record?.mobile_whatsapp;
    },

    async sendWhatsappMessage() {
        const message = this.composerRef.el.querySelector('.o_composer_text_field').value;
        await this.props.record.action_send_whatsapp(message);
        this.composerRef.el.querySelector('.o_composer_text_field').value = '';
    },
});
