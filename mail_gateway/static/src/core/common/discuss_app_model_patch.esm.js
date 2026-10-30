/* @odoo-module */

import {DiscussApp} from "@mail/core/common/discuss_app_model";
import {Record} from "@mail/core/common/record";

import {_t} from "@web/core/l10n/translation";
import {patch} from "@web/core/utils/patch";

patch(DiscussApp, {
    new(data) {
        const res = super.new(data);
        res.gateway = {
            extraClass: "o-mail-DiscussSidebarCategory-gateway",
            id: "gateway",
            name: _t("Gateway"),
            isOpen: false,
            canView: false,
            canAdd: true,
            addTitle: _t("Search Gateway Channel"),
            serverStateKey: "is_discuss_sidebar_category_gateway_open",
        };
        return res;
    },
});

patch(DiscussApp.prototype, {
    setup(env) {
        super.setup(env);
        this.gateway = Record.one("DiscussAppCategory");
    },
});
