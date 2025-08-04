/** @odoo-module **/

/* Copyright 2025 Kencove - Mohamed Alkobrosli
    License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html). */

import {registry} from "@web/core/registry";
import {useService} from "@web/core/utils/hooks";
import {initializeDesignTabCss} from "mass_mailing.design_constants";
// Import {HtmlField} from "@web_editor/js/backend/html_field";
import {MassMailingHtmlField} from "@mass_mailing/js/mass_mailing_html_field";

const {useSubEnv, onWillUpdateProps} = owl;

export class MailTemplateHtmlField extends MassMailingHtmlField {
    setup() {
        super.setup();
        useSubEnv({
            onWysiwygReset: this._resetIframe.bind(this),
        });
        this.action = useService("action");
        this.rpc = useService("rpc");
        this.dialog = useService("dialog");
        onWillUpdateProps(() => {
            // If (this.props.record.data.mailing_model_id && this.wysiwyg) {
            //     this._hideIrrelevantTemplates();
            // }
        });
    }
    async _resetIframe() {
        if (this._switchingTheme) {
            return;
        }
        this.wysiwyg.$iframeBody.find(".o_mail_theme_selector_new").remove();
        // Await this._onSnippetsLoaded();
        // Data is removed on save but we need the mailing and its body to be
        // named so they are handled properly by the snippets menu.
        this.wysiwyg.$iframeBody.find(".o_layout").addBack().data("name", "Mailing");
        // We don't want to drop snippets directly within the wysiwyg.
        this.wysiwyg.$iframeBody
            .find(".odoo-editor-editable")
            .removeClass("o_editable");
        initializeDesignTabCss(this.wysiwyg.getEditable());
        this.wysiwyg.getEditable().find("img").attr("loading", "");
        this.wysiwyg.odooEditor.observerFlush();
        this.wysiwyg.odooEditor.historyReset();
        this.wysiwyg.$iframeBody.addClass("o_mass_mailing_iframe");
        this.onIframeUpdated();
    }
}

registry.category("fields").add("mail_template_html_extended", MailTemplateHtmlField);
