/** @odoo-module **/

import {SocialCommentDialog} from "@social_media_sync/components/social_comment_dialog/social_comment_dialog.esm";
import {SocialKanbanRecord} from "@social_media_base/js/views/kanban/social_kanban_record.esm";
import {_t} from "@web/core/l10n/translation";
import {patch} from "@web/core/utils/patch";
import {useDelegatedClick} from "@social_media_base/js/app/social_delegated_click.esm";
import {useService} from "@web/core/utils/hooks";

/**
 * The card is patched instead of moved: it is one class that also draws the
 * images and the renderer is what registers it, so base has to keep owning
 * it. What comes back here is only what talks to the social media — reacting
 * and commenting.
 */
patch(SocialKanbanRecord.prototype, {
    /** @override */
    setup() {
        super.setup();
        this.effectService = useService("effect");
        // Which social media serve each half of the footer, read by its
        // template. This module holds the thread and the reactions, but what
        // answers them for a given social media is its bridge, so the lists
        // are empty here and every bridge adds its own media to the ones it
        // serves. They are lists and not answers computed from the record:
        // `setup` runs before the fields of the card are there, so the social
        // media of the publication is only known when the template is
        // rendered.
        this.record.syncCapabilities = {
            statistics: [],
            reactions: [],
            comments: [],
        };

        useDelegatedClick(
            this.rootRef,
            ".social-like-post",
            this.onLikePost.bind(this)
        );
        useDelegatedClick(
            this.rootRef,
            ".social-post-comment",
            this.onPostComment.bind(this)
        );
    },

    /**
     * Toggle the reaction of the account on the publication.
     *
     * A social media holds one reaction per account, so the entry is not a
     * one-way action: pressing it on a publication the account already
     * recommended is what withdraws the reaction.
     *
     * @param {Event} ev the click on the entry of the card.
     */
    async onLikePost(ev) {
        ev.stopPropagation();
        const liked = Boolean(this.record.liked_by_account?.raw_value);
        const response = liked
            ? await this.env.model.onUnlikePost(this.record)
            : await this.env.model.onLikePost(this.record);

        // Reacting is one of the moments the social media reports the
        // publication as gone, and the record still says it is online until
        // the card is redrawn.
        if (
            !this.record.post_account_url.value ||
            (response && response.post_deleted)
        ) {
            this.env.model.load();
        }
        if (response && response.success && liked) {
            this.notification.add(_t("You have withdrawn your recommendation."), {
                type: "success",
            });
        } else if (response && response.success) {
            this.effectService.add({
                type: "rainbow_man",
                message: _t("You have liked the post."),
                imgUrl: "/social_media_base/static/src/img/like.png",
                fadeout: "fast",
            });
        } else if (response && response.message) {
            this.notification.add(response.message, {type: "info"});
        }
    },

    onPostComment(ev) {
        ev.stopPropagation();
        this.dialog.add(SocialCommentDialog, {
            title: _t("Comments"),
            account: this.record.account_id,
            post: this.record,
            media_type: this.record.media_type,
            images: JSON.parse(this.record.image_urls.raw_value),
        });
    },
});
