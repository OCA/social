/** @odoo-module **/

import {PhoneField} from "@web/views/fields/phone/phone_field";
import {SendWhatsappButton} from "@mail_gateway_whatsapp/components/send_whatsapp_button/send_whatsapp_button.esm";
import {patch} from "@web/core/utils/patch";
patch(PhoneField, "mail_gateway_whatsapp.PhoneField", {
    components: {
        ...PhoneField.components,
        SendWhatsappButton,
    },
    defaultProps: {
        ...PhoneField.defaultProps,
        enableButton: true,
    },
    props: {
        ...PhoneField.props,
        enableButton: {type: Boolean, optional: true},
    },
    extractProps: ({attrs}) => {
        return {
            enableButton: attrs.options.enable_sms,
            placeholder: attrs.placeholder,
        };
    },
});
