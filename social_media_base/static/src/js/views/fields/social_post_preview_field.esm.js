/** @odoo-module **/

import {Component, useEffect, useRef} from "@odoo/owl";
import {
    MESSAGE_EXPANDED_CLASS,
    isMessageClamped,
    messageToggleLabel,
} from "@social_media_base/components/social_message/social_message.esm";
import {_t} from "@web/core/l10n/translation";
import {registry} from "@web/core/registry";
import {standardFieldProps} from "@web/views/fields/standard_field_props";

/**
 * Read only widget drawing the preview of a post.
 *
 * The preview is rendered on the server, one template per social media, so
 * the message cannot be drawn with the component the cards use: the template
 * writes out the HTML it receives -- an ``html`` field reaches the client as
 * ``Markup`` -- and the widget only wires it. What "cut" means -- how it is
 * measured, what the link says, which class shows the message whole -- is
 * the component's, so the two never say different things.
 */
export class SocialPostPreviewField extends Component {
    setup() {
        this.rootRef = useRef("root");

        useEffect(
            (element) => element && this._setupMessages(element),
            () => [this.rootRef.el, this.props.record.data[this.props.name]]
        );
    }

    /**
     * Wire the link that unfolds every message of the preview.
     *
     * @param {HTMLElement} element root of the rendered preview.
     * @returns {Function} unwiring of the links.
     */
    _setupMessages(element) {
        const cleanups = [];
        for (const message of element.querySelectorAll(".o_social_message")) {
            const toggle = message.nextElementSibling;
            if (!toggle || !toggle.classList.contains("show-more-message")) {
                continue;
            }
            const clamped = isMessageClamped(message);
            toggle.classList.toggle("d-none", !clamped);
            if (!clamped) {
                continue;
            }
            const onClick = () => {
                const expanded = message.classList.toggle(MESSAGE_EXPANDED_CLASS);
                toggle.textContent = messageToggleLabel(expanded);
            };
            toggle.addEventListener("click", onClick);
            cleanups.push(() => toggle.removeEventListener("click", onClick));
        }
        return () => cleanups.forEach((cleanup) => cleanup());
    }
}

SocialPostPreviewField.template = "social_media_base.SocialPostPreviewField";
SocialPostPreviewField.props = {...standardFieldProps};

export const socialPostPreviewField = {
    component: SocialPostPreviewField,
    displayName: _t("Social Post Preview"),
    supportedTypes: ["html"],
};

registry.category("fields").add("social_post_preview", socialPostPreviewField);
