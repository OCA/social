/** @odoo-module **/

import {registerPatch} from "@mail/model/model_core";
import "@mail/models/composer_view";
import Dialog from "web.Dialog";
import core from "web.core";
const _t = core._t;

registerPatch({
    name: "ComposerView",
    recordMethods: {
        /**
         * @override
         */
        onClickSend() {
            const composerModel = this;
            if (this.composer.isLog) {
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
                                composerModel._super();
                            },
                        },
                        {text: _t("Discard"), close: true},
                    ],
                });
                this.dialog.open();
            }
        },
    },
});
