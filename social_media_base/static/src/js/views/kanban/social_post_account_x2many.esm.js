/** @odoo-module **/

import {X2ManyField, x2ManyField} from "@web/views/fields/x2many/x2many_field";
import {KanbanRecord} from "@web/views/kanban/kanban_record";
import {KanbanRenderer} from "@web/views/kanban/kanban_renderer";
import {SocialMessage} from "@social_media_base/components/social_message/social_message.esm";
import {SocialPostAccountMixin} from "@social_media_base/js/app/social_post_account_mixin.esm";
import {registry} from "@web/core/registry";
import {useEffect} from "@odoo/owl";
import {useService} from "@web/core/utils/hooks";

/** Read only card of a publication embedded in the post form. */
export class SocialPostAccountRecord extends SocialPostAccountMixin(KanbanRecord) {
    /** @override */
    setup() {
        super.setup();
        this.record.countShowImage = 2;
        this.dialogService = useService("dialog");
        this._bindClick(".social-all-images", this.onShowAllImages);
    }

    _bindClick(selector, handler) {
        useEffect(
            (element) => {
                if (element) {
                    const listener = handler.bind(this);
                    element.addEventListener("click", listener);
                    return () => element.removeEventListener("click", listener);
                }
            },
            () => [this.rootRef.el.querySelector(selector)]
        );
    }
}

SocialPostAccountRecord.components = {
    ...KanbanRecord.components,
    SocialMessage,
};

export class SocialPostAccountRenderer extends KanbanRenderer {}

SocialPostAccountRenderer.components = {
    ...KanbanRenderer.components,
    KanbanRecord: SocialPostAccountRecord,
};

export class SocialPostAccountX2ManyField extends X2ManyField {}

SocialPostAccountX2ManyField.components = {
    ...X2ManyField.components,
    KanbanRenderer: SocialPostAccountRenderer,
};

export const socialPostAccountX2ManyField = {
    ...x2ManyField,
    component: SocialPostAccountX2ManyField,
};

registry
    .category("fields")
    .add("social_post_account_kanban", socialPostAccountX2ManyField);
