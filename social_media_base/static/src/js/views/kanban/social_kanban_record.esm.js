/** @odoo-module **/
import {KanbanRecord} from "@web/views/kanban/kanban_record";
import {SocialMessage} from "@social_media_base/components/social_message/social_message.esm";
import {SocialPostAccountMixin} from "@social_media_base/js/app/social_post_account_mixin.esm";
import {_t} from "@web/core/l10n/translation";
import {useEffect} from "@odoo/owl";
import {useService} from "@web/core/utils/hooks";

export class SocialKanbanRecord extends SocialPostAccountMixin(KanbanRecord) {
    /** @override */
    setup() {
        super.setup();
        this.record.countShowImage = 2;
        this.dialogService = useService("dialog");
        this.effectService = useService("effect");
        this.orm = useService("orm");
        this.messageNotExistPost = _t("The post does not exist or has been deleted.");

        useEffect(
            (value) => {
                if (value) {
                    const listener = this.onShowAllImages.bind(this);
                    value.addEventListener("click", listener);
                    return () => {
                        value.removeEventListener("click", listener);
                    };
                }
            },
            () => [this.rootRef.el.querySelector(".social-all-images")]
        );
    }

    /**
     * Whether the publication is still worth opening.
     *
     * Base answers yes without asking anybody: verifying costs one call per
     * publication, which is the kind of cost that grows with the history of
     * the account and does not belong here. A synchronization module is what
     * turns this into a real check.
     *
     * @returns {Promise<Boolean>}
     */
    async validPostExist() {
        return true;
    }

    messagePostNotExist() {
        this.notification.add(this.messageNotExistPost, {
            type: "info",
        });
    }

    /** @override */
    async onGlobalClick(ev) {
        const kanbanSocial = ev.target.closest("div.oe_kanban_social_dashboard");
        if (kanbanSocial !== null && !this.record.post_account_url.value) {
            this.messagePostNotExist();
            this.env.model.load();
        } else if (kanbanSocial !== null && this.record.post_account_url.raw_value) {
            const postExist = await this.validPostExist();
            if (postExist) {
                window.open(this.record.post_account_url.value, "_blank");
            } else {
                this.messagePostNotExist();
                this.env.model.load();
            }
        }
        return super.onGlobalClick(ev);
    }
}

SocialKanbanRecord.components = {
    ...KanbanRecord.components,
    SocialMessage,
};
