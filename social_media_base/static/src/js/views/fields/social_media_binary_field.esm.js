/** @odoo-module **/

import {
    Many2ManyBinaryField,
    many2ManyBinaryField,
} from "@web/views/fields/many2many_binary/many2many_binary_field";
import {registry} from "@web/core/registry";

/**
 * `many2many_binary` listing the medias in the order they were added.
 *
 * `ir.attachment` is ordered by `id desc` and a many2many is read with the
 * order of its comodel, so a post read back from database gives the widget
 * its images newest first. Everything else that draws or publishes them goes
 * through `_sorted_medias`, which puts them back in the order the user added
 * them: without this the form is the only surface disagreeing with the
 * preview, the cards and what reaches the social media.
 *
 * The identifier of an attachment grows with time, so ordering by it is the
 * same criterion the server applies.
 */
export class SocialMediaBinaryField extends Many2ManyBinaryField {
    /** @override */
    get files() {
        return super.files.sort((first, second) => first.id - second.id);
    }
}

export const socialMediaBinaryField = {
    ...many2ManyBinaryField,
    component: SocialMediaBinaryField,
};

registry.category("fields").add("social_media_binary", socialMediaBinaryField);
