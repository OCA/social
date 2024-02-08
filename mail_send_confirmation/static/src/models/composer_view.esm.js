/* @odoo-module */

import {Composer} from "@mail/core/common/composer";
import {ConfirmationDialog} from "@web/core/confirmation_dialog/confirmation_dialog";
import {_t} from "@web/core/l10n/translation";
import {patch} from "@web/core/utils/patch";
import {useService} from "@web/core/utils/hooks";

patch(Composer.prototype, {
    /**
     * @override
     */
    setup() {
        super.setup();
        this.dialogService = useService("dialog");
    },
    async sendMessage() {
        if (this.props.type === "message") {
            this.dialogService.add(ConfirmationDialog, {
                body: _t(
                    "This message will be sent to external partners as well. Are you sure you would like to send this message?"
                ),
                confirm: async () => {
                    super.sendMessage();
                },
                cancel: () => {
                    /* We need this empty function to display the cancel button */
                },
            });
        } else {
            super.sendMessage();
        }
    },
});
