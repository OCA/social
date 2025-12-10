/** @odoo-module */

import {NotificationItem} from "@mail/core/web/notification_item";
import {patch} from "@web/core/utils/patch";
import {useService} from "@web/core/utils/hooks";

patch(NotificationItem.prototype, {
    setup() {
        super.setup();
        this.action = useService("action");
    },

    /**
     * Navigate to the document when clicking on the display name.
     * @param {MouseEvent} ev
     */
    onClickDisplayName(ev) {
        ev.stopPropagation();
        const {resModel, resId} = this.props;
        if (resModel && resId) {
            this.action.doAction({
                type: "ir.actions.act_window",
                res_model: resModel,
                res_id: resId,
                views: [[false, "form"]],
            });
        }
    },
});

NotificationItem.props.push("resModel?", "resId?");
