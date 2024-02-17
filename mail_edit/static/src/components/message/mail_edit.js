/* Copyright 2023 Therp BV <https://www.therp.nl>
 * License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
 */
odoo.define("mail_edit/static/src/components/message/mail_edit.js", function (require) {
    "use strict";

    const components = {
        Message: require("mail/static/src/components/message/message.js"),
    };
    const {patch} = require("web.utils");
    var Dialog = require("web.Dialog");
    var core = require("web.core");
    var _t = core._t;

    patch(components.Message, "mail_edit.main", {
        async _onClickMessageEdit(ev) {
            ev.stopPropagation();
            var self = this;
            const action = await this.rpc({
                route: "/web/action/load",
                params: {action_id: "mail_edit.mail_edit_action"},
            });
            action.res_id = this.message.id;
            await new Promise((resolve) =>
                this.env.bus.trigger("do-action", {
                    action: action,
                    options: {
                        on_close: async () => {
                            resolve();

                            const [data] = await self.env.services.rpc(
                                {
                                    model: "mail.message",
                                    method: "message_format",
                                    args: [self.message.id],
                                },
                                {shadow: true}
                            );
                            let shouldDelete = false;
                            if (data) {
                                self.message.update(
                                    self.env.models["mail.message"].convertData(data)
                                );
                            } else {
                                shouldDelete = true;
                            }
                            if (shouldDelete) {
                                self.message.delete();
                            }
                        },
                    },
                })
            );
        },
        async _onClickMessageDelete(ev) {
            ev.stopPropagation();
            var self = this;
            const promptText = _t("Do you really want to delete this message?");
            Dialog.confirm(this, promptText, {
                confirm_callback: async function () {
                    await self.env.services.rpc({
                        model: "mail.message",
                        method: "unlink",
                        args: [self.message.id],
                    });
                    await self.message.delete();
                },
            });
        },
    });
});
