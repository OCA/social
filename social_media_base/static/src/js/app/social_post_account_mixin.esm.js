/** @odoo-module */
import {SocialImageDialog} from "../../components/social_image_dialog/social_image_dialog.esm";
import {_t} from "@web/core/l10n/translation";
import {useDelegatedClick} from "./social_delegated_click.esm";

/**
 * The nodes of a card that open the gallery: the counter of the medias the
 * card does not draw, and the images themselves.
 */
const SHOW_ALL_IMAGES_SELECTOR = ".social-all-images, .social-post-images";

/** How many medias a card draws before offering the gallery. */
export const SHOWN_IMAGE_COUNT = 2;

export const SocialPostAccountMixin = (T) =>
    class extends T {
        /** @override */
        setup() {
            super.setup();
            // Written on the record and not read from the component: the
            // arch of a kanban card is compiled without its members.
            this.record.countShowImage = SHOWN_IMAGE_COUNT;
        }

        /**
         * Open the gallery from every node of the card that offers it.
         *
         * Call it from `setup`: it installs a hook.
         */
        bindShowAllImages() {
            useDelegatedClick(
                this.rootRef,
                SHOW_ALL_IMAGES_SELECTOR,
                this.onShowAllImages.bind(this)
            );
        }

        onShowAllImages(ev) {
            ev.stopPropagation();
            this.dialog.add(SocialImageDialog, {
                title: _t("All Images"),
                images: JSON.parse(this.record.image_urls.raw_value),
                fullscreen: true,
            });
        }
    };
