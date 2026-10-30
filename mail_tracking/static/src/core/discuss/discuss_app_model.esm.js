/** @odoo-module */

import {DiscussApp} from "@mail/core/common/discuss_app_model";
import {Record} from "@mail/core/common/record";
import {patch} from "@web/core/utils/patch";

/** @type {import("@mail/core/web/discuss_app_model").DiscussApp} */
const DiscussAppPatch = {
    setup() {
        super.setup();
        this.failed = Record.one("Thread");
    },
};

patch(DiscussApp.prototype, DiscussAppPatch);
