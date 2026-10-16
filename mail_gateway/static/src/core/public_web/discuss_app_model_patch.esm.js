import {DiscussApp} from "@mail/core/public_web/discuss_app_model";
import {_t} from "@web/core/l10n/translation";
import {fields} from "@mail/core/common/record";

import {patch} from "@web/core/utils/patch";

patch(DiscussApp.prototype, {
    setup() {
        super.setup(...arguments);
        this.gateway = fields.One("discuss.category", {
            compute() {
                return {
                    canView: false,
                    extraClass: "o-mail-DiscussSidebarCategory-gateway",
                    icon: "fa fa-plane",
                    id: "gateway",
                    name: _t("Gateway"),
                    sequence: 20,
                    serverStateKey: "is_discuss_sidebar_category_gateway_open",
                };
            },
            eager: true,
        });
    },
});
