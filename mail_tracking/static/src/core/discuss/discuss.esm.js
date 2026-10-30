/* @odoo-module */

import {Discuss} from "@mail/core/common/discuss";
import {patch} from "@web/core/utils/patch";
import {useService} from "@web/core/utils/hooks";

patch(Discuss.prototype, {
    setup() {
        super.setup(...arguments);
        this.dialogService = useService("dialog");
    },
});
