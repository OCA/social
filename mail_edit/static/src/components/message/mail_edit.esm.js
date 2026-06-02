/** @odoo-module **/

/* Copyright 2023 Therp BV <https://www.therp.nl>
 * License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
 */

import {registerPatch} from "@mail/model/model_core";
import {one} from "@mail/model/model_field";
import {clear} from "@mail/model/model_field_command";

registerPatch({
    name: "MessageAction",
    fields: {
        messageActionListOwnerAsMove: one("MessageActionList", {
            identifying: true,
            inverse: "actionMove",
        }),

        sequence: {
            compute() {
                if (this.messageActionListOwnerAsMove) {
                    return 9;
                }
                return this._super();
            },
        },

        messageActionListOwner: {
            compute() {
                if (this.messageActionListOwnerAsMove) {
                    return this.messageActionListOwnerAsMove;
                }
                return this._super();
            },
        },
    },
});

registerPatch({
    name: "MessageActionList",
    fields: {
        actionMove: one("MessageAction", {
            compute() {
                const message = this.message;
                const canMoveMessage =
                    message &&
                    message.id &&
                    ["comment", "email"].includes(message.message_type);

                if (this.actionEdit || canMoveMessage) {
                    return {};
                }
                return clear();
            },
            inverse: "messageActionListOwnerAsMove",
        }),
    },
});

registerPatch({
    name: "MessageActionView",
    recordMethods: {
        async _openMailEditWizard(message, isMove) {
            const action = await this.env.services.rpc("/web/action/load", {
                action_id: "mail_edit.mail_edit_action",
            });

            action.res_id = message.id;

            await this.env.services.action.doAction(action, {
                onClose: async () => {
                    await this._onMailEditWizardClose(message, isMove);
                },
            });
        },

        async _onMailEditWizardClose(message, isMove) {
            const data = await this.env.services.orm.call(
                "mail.message",
                "message_format",
                [[message.id]],
                {},
                {shadow: true}
            );

            if (!data || !data.length) {
                message.delete();
                return;
            }

            const MessageModel =
                this.messaging.models["mail.message"] || this.messaging.models.Message;

            message.update(MessageModel.convertData(data[0]));

            this.env.services.notification.add(this._getSuccessMessage(isMove), {
                title: this._getSuccessTitle(isMove),
                type: "success",
                sticky: true,
            });
        },

        _getSuccessMessage(isMove) {
            if (isMove) {
                return this.env._t(
                    "Message moved successfully, refresh to see changes."
                );
            }
            return this.env._t("Message edited successfully.");
        },

        _getSuccessTitle(isMove) {
            if (isMove) {
                return this.env._t("Message moved");
            }
            return this.env._t("Message edited");
        },

        async _reloadCurrentAction() {
            await this.env.services.action.doAction({
                type: "ir.actions.client",
                tag: "reload",
            });
        },

        async onClick(ev) {
            if (this.messageAction.messageActionListOwnerAsEdit) {
                ev.stopPropagation();

                await this._openMailEditWizard(
                    this.messageAction.messageActionListOwner.message,
                    false
                );
                return;
            }

            if (this.messageAction.messageActionListOwnerAsMove) {
                ev.stopPropagation();
                this._notifyMoveHelp();

                await this._openMailEditWizard(
                    this.messageAction.messageActionListOwner.message,
                    true
                );
                return;
            }

            return this._super(...arguments);
        },

        _notifyMoveHelp() {
            this.env.services.notification.add(
                this.env._t("Change 'Destination Object' in the wizard, then save."),
                {
                    title: this.env._t("Move message"),
                    type: "info",
                    sticky: true,
                }
            );
        },
    },

    fields: {
        title: {
            compute() {
                if (this.messageAction.messageActionListOwnerAsMove) {
                    return this.env._t("Move message");
                }
                return this._super();
            },
        },

        classNames: {
            compute() {
                if (this.messageAction.messageActionListOwnerAsMove) {
                    return [
                        this.paddingClassNames,
                        "fa",
                        "fa-lg",
                        "fa-hand-o-right",
                        "o_MessageActionView_actionMove",
                    ].join(" ");
                }
                return this._super();
            },
        },
    },
});
