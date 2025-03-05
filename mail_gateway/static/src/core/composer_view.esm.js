/** @odoo-module **/

import {clear} from "@mail/model/model_field_command";
import {escapeAndCompactTextContent} from "@mail/js/utils";
import {one} from "@mail/model/model_field";
import {registerPatch} from "@mail/model/model_core";

registerPatch({
    name: "ComposerView",
    recordMethods: {
        _getMessageData() {
            var result = this._super(...arguments);
            if (this.composer.isGateway) {
                result.gateway_notifications =
                    this.composer.composerGatewayFollowers.map((follower) => {
                        return follower._getMessageData();
                    });
            }
            return result;
        },
        async openFullComposer() {
            if (this.composer.isGateway) {
                const attachmentIds = this.composer.attachments.map(
                    (attachment) => attachment.id
                );
                const context = {
                    default_attachment_ids: attachmentIds,
                    default_body: escapeAndCompactTextContent(
                        this.composer.textInputContent
                    ),
                    default_model: this.composer.activeThread.model,
                    default_partner_ids: this.composer.recipients.map(
                        (partner) => partner.id
                    ),
                    default_res_id: this.composer.activeThread.id,
                    mail_post_autofollow: this.composer.activeThread.hasWriteAccess,
                    default_wizard_partner_ids: Array.from(
                        new Set(
                            this.composer.composerGatewayFollowers.map((follower) => {
                                return follower.follower.partner.id;
                            })
                        )
                    ),
                    default_wizard_channel_ids: Array.from(
                        new Set(
                            this.composer.composerGatewayFollowers.map((follower) => {
                                return follower.channel;
                            })
                        )
                    ),
                };
                const action = {
                    type: "ir.actions.act_window",
                    name: this.env._t("Gateway message"),
                    res_model: "mail.compose.gateway.message",
                    view_mode: "form",
                    views: [[false, "form"]],
                    target: "new",
                    context: context,
                };
                const composer = this.composer;
                const options = {
                    onClose: () => {
                        if (!composer.exists()) {
                            return;
                        }
                        composer._reset();
                        if (composer.activeThread) {
                            composer.activeThread.fetchData(["messages"]);
                        }
                    },
                };
                await this.env.services.action.doAction(action, options);
                return;
            }
            return await this._super(...arguments);
        },
    },
    fields: {
        hasFollowers: {
            compute() {
                if (this.composer.isGateway) {
                    return false;
                }
                return this._super();
            },
        },
        hasHeader: {
            compute() {
                return Boolean(this._super() || this.composer.isGateway);
            },
        },
        composerGatewayChannelView: one("GatewayChannelView", {
            compute() {
                if (this.composer.isGateway) {
                    return {};
                }
                return clear();
            },
            inverse: "composerViewOwner",
        }),
    },
});
