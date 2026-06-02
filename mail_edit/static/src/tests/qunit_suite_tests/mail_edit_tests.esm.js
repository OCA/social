/** @odoo-module **/

/* global QUnit */

import {patchWithCleanup} from "@web/../tests/helpers/utils";
import {click, contains} from "@web/../tests/utils";
import {start, startServer} from "@mail/../tests/helpers/test_utils";

QUnit.module("mail_edit", {}, function () {
    QUnit.module("MessageActionView");

    QUnit.test("move action opens edit wizard", async function (assert) {
        const pyEnv = await startServer();
        const partnerId = pyEnv["res.partner"].create({
            name: "Mail Edit Test Partner",
        });

        const messageId = pyEnv["mail.message"].create({
            body: "<p>Message to move</p>",
            model: "res.partner",
            res_id: partnerId,
            message_type: "email",
            record_name: "Mail Edit Test Partner",
        });

        const {env, openView} = await start();

        patchWithCleanup(env.services, {
            async rpc(route, params) {
                if (route === "/web/action/load") {
                    assert.strictEqual(
                        params.action_id,
                        "mail_edit.mail_edit_action",
                        "loads the mail edit action"
                    );
                    return {
                        type: "ir.actions.act_window",
                        res_model: "mail.message",
                        res_id: false,
                        views: [[false, "form"]],
                        target: "new",
                    };
                }
                return this._super(...arguments);
            },
        });

        patchWithCleanup(env.services.notification, {
            add(message, options) {
                assert.strictEqual(
                    options.title,
                    env._t("Move message"),
                    "shows the move helper notification"
                );
                assert.strictEqual(
                    options.type,
                    "info",
                    "move helper notification is informational"
                );
                return this._super(...arguments);
            },
        });

        patchWithCleanup(env.services.action, {
            async doAction(action) {
                if (action.res_model !== "mail.message") {
                    return this._super(...arguments);
                }

                assert.strictEqual(
                    action.res_id,
                    messageId,
                    "opens the wizard on the clicked message"
                );
                assert.strictEqual(
                    action.res_model,
                    "mail.message",
                    "opens the mail.message wizard"
                );
            },
        });

        await openView({
            res_model: "res.partner",
            res_id: partnerId,
            views: [[false, "form"]],
        });

        await contains(".o_Message");
        await click(".o_MessageActionView_actionMove");
    });
});
