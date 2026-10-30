/* @odoo-module */

import {_t} from "@web/core/l10n/translation";
import {ConfirmationDialog} from "@web/core/confirmation_dialog/confirmation_dialog";
import {threadActionsRegistry} from "@mail/core/common/thread_actions";

threadActionsRegistry.add("mark-failed-all-reviewed", {
    condition(component) {
        return component.thread?.id === "failed";
    },
    disabledCondition(component) {
        return component.thread.isEmpty;
    },
    open(component) {
        component.dialogService.add(ConfirmationDialog, {
            body: _t("Do you really want to mark as reviewed all the failed messages?"),
            cancel: () => {
                return;
            },
            confirm: () =>
                component.orm.silent.call("mail.message", "set_all_as_reviewed"),
        });
    },
    sequence: 1,
    text: _t("Mark all as reviewed"),
});
