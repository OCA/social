/** @odoo-module **/

import {Component} from "@odoo/owl";
import {SocialMessage} from "@social_media_base/components/social_message/social_message.esm";
import {_t} from "@web/core/l10n/translation";
import {registry} from "@web/core/registry";
import {standardFieldProps} from "@web/views/fields/standard_field_props";

/**
 * Read only widget drawing a text field as the message of a post: cut to a
 * number of lines with a link to unfold it.
 *
 * It exists so the same block can be used in kanban views that have no
 * `js_class` of their own -- the posts of a campaign -- where a component
 * cannot be reached but a widget can.
 */
export class SocialMessageField extends Component {
    get message() {
        return this.props.record.data[this.props.name] || "";
    }
}

SocialMessageField.template = "social_media_base.SocialMessageField";
SocialMessageField.components = {SocialMessage};
SocialMessageField.props = {
    ...standardFieldProps,
    lines: {type: Number, optional: true},
};

export const socialMessageField = {
    component: SocialMessageField,
    displayName: _t("Social Message"),
    supportedTypes: ["char", "text"],
    supportedOptions: [
        {
            label: _t("Lines"),
            name: "lines",
            type: "number",
            help: _t("Number of lines shown before the message is cut."),
        },
    ],
    extractProps: ({options}) => ({lines: options.lines || undefined}),
};

registry.category("fields").add("social_message", socialMessageField);
