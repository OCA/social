/** @odoo-module **/
/*
    Copyright 2022 Camptocamp SA (https://www.camptocamp.com).
    @author Iván Todorovich <ivan.todorovich@camptocamp.com>
    License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
*/

import {registerClassPatchModel, registerFieldPatchModel} from "@mail/model/model_core";
import {attr} from "@mail/model/model_field";

registerClassPatchModel("mail.activity", "mail_activity_security/models/activity.js", {
    /**
     * @override
     */
    convertData(data) {
        const data2 = this._super(data);
        if ("user_can_mark_as_done" in data) {
            data2.canMarkAsDone = data.user_can_mark_as_done;
        }
        if ("user_can_edit" in data) {
            data2.canEdit = data.user_can_edit;
        }
        if ("user_can_cancel" in data) {
            data2.canCancel = data.user_can_cancel;
        }
        return data2;
    },
});

registerFieldPatchModel("mail.activity", "mail_activity_security/models/activity.js", {
    canMarkAsDone: attr({default: true}),
    canEdit: attr({default: true}),
    canCancel: attr({default: true}),
});
