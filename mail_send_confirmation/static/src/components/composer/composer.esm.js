/** @odoo-module */

import {Composer} from "@mail/components/composer/composer";
import {patch} from "web.utils";
import Dialog from "web.Dialog";
import core from "web.core";
const _t = core._t;

patch(
    Composer.prototype,
    "mail_send_confirmation/static/src/components/composer/composer.js",
    {
        // --------------------------------------------------------------------------
        // Handlers
        // --------------------------------------------------------------------------

        /**
         * Small override that asks for confirmation in case when send mail to customer.
         *
         * @override
         */
        _onClickSend() {
            const superMethod = this._super;
            if (this.composerView.composer.isLog) {
                this._super();
            } else {
                this.dialog = new Dialog(this, {
                    title: _t("Confirmation"),
                    $content: $("<div/>", {
                        text: _.str.sprintf(
                            _t(
                                "This message will be sent to external partners as well. Are you sure you would like to send this message?"
                            )
                        ),
                    }),
                    buttons: [
                        {
                            text: _t("Confirm"),
                            classes: "btn-primary",
                            close: true,
                            click: function () {
                                superMethod();
                            },
                        },
                        {text: _t("Discard"), close: true},
                    ],
                });
                this.dialog.open();
            }
        },
    }
);
