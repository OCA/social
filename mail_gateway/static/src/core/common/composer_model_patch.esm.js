import {Composer} from "@mail/core/common/composer_model";
import {patch} from "@web/core/utils/patch";
import {url} from "@web/core/utils/urls";

patch(Composer, {
    get resUrl() {
        if (!this.gateway_thread_data) {
            return super.resUrl;
        }
        return `${url("/web")}#model=${this.gateway_thread_data.model}&id=${
            this.gateway_thread_data.id
        }`;
    },
});

patch(Composer.prototype, {
    setup() {
        super.setup();
        this.gateway_channel = false;
        this.gateway_partner = false;
    },
});
