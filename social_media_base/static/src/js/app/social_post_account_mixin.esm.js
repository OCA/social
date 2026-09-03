/** @odoo-module */
import {SocialImageDialog} from "../../components/social_image_dialog/social_image_dialog.esm";
import {_t} from "@web/core/l10n/translation";

export const SocialPostAccountMixin = (T) =>
    class extends T {
        onShowAllImages(ev) {
            ev.stopPropagation();
            this.dialogService.add(SocialImageDialog, {
                title: _t("All Images"),
                images: JSON.parse(this.record.image_urls.raw_value),
                fullscreen: true,
            });
        }

        async onLikePost(ev) {
            ev.stopPropagation();
            const response = await this.env.model.onLikePost(this.record);

            // A like is one of the moments the social media reports the
            // publication as gone, and the record still says it is online
            // until the card is redrawn.
            if (
                !this.record.post_account_url.value ||
                (response && response.post_deleted)
            ) {
                this.env.model.load();
            }
            if (response && response.success) {
                this.effectService.add({
                    type: "rainbow_man",
                    message: _t("You have liked the post."),
                    imgUrl: "/social_media_base/static/src/img/like.png",
                    fadeout: "fast",
                });
            } else if (response && response.message) {
                this.notification.add(response.message, {type: "info"});
            }
        }
    };
