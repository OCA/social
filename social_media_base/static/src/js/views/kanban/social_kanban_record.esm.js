/** @odoo-module **/
import {KanbanRecord} from "@web/views/kanban/kanban_record";
import {SocialMessage} from "@social_media_base/components/social_message/social_message.esm";
import {SocialPostAccountMixin} from "@social_media_base/js/app/social_post_account_mixin.esm";
import {_t} from "@web/core/l10n/translation";
import {useService} from "@web/core/utils/hooks";

export class SocialKanbanRecord extends SocialPostAccountMixin(KanbanRecord) {
    /** @override */
    setup() {
        super.setup();
        this.orm = useService("orm");
        this.messageNotExistPost = _t("The post does not exist or has been deleted.");
        this.bindShowAllImages();
    }

    /**
     * Whether the publication is still worth opening.
     *
     * One call for the one publication the user clicked, which is a cost
     * that does not grow with the history of the account. What the answer is
     * worth depends on the connector: one that does not implement the check
     * answers from the remote reference alone.
     *
     * @returns {Promise<Boolean>}
     */
    async validPostExist() {
        const postAccountId = this.record.id.raw_value;
        if (!postAccountId) {
            return false;
        }
        return await this.orm.call("social.post.account", "check_post_exists", [
            postAccountId,
        ]);
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
