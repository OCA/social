/** @odoo-module **/

import {Component, onMounted, onWillStart, onWillUnmount, useState} from "@odoo/owl";
import {useBus, useService} from "@web/core/utils/hooks";
import {Dialog} from "@web/core/dialog/dialog";
import {SocialComment} from "../social_comment/social_comment.esm";
import {SocialComposer} from "../social_composer/social_composer.esm";
import {SocialImageDialog} from "@social_media_base/components/social_image_dialog/social_image_dialog.esm";
import {SocialMessage} from "@social_media_base/components/social_message/social_message.esm";
import {_t} from "@web/core/l10n/translation";

export class SocialCommentDialog extends Component {
    static template = "social_media_sync.SocialCommentDialog";
    static components = {
        Dialog,
        SocialComposer,
        SocialComment,
        // The dialog shares the block of the card with the kanban views, and
        // that block draws the message with this component. The dialog shows
        // the message whole, so the branch is never taken, but the template
        // is the same one and it is resolved against the components of
        // whoever calls it.
        SocialMessage,
    };
    static props = {
        title: {type: String, required: true},
        images: {type: Array, required: true},
        post: {type: Object, required: true},
        account: {type: Object, required: true},
        media_type: {type: Object, required: true},
        close: {type: Function},
    };

    setup() {
        super.setup();
        this.dialogService = useService("dialog");
        this.socialService = useService("social_service");
        this.threadService = useService("mail.thread");
        this.notificationService = useService("notification");
        this.busService = this.env.services.bus_service;
        this.record = this.props.post;
        // The aim of the composer lives in the service, and the dialog has
        // to redraw when a comment takes it or gives it back: the composer
        // moves from the head of the dialog to under that comment.
        this.socialState = useState(this.socialService.state);
        // The aim the publication took away, kept so a comment the social
        // media rejects can have it back: the retry starts pointing at the
        // same comment instead of asking the user to aim again.
        this.lastReplyTarget = null;
        this.state = useState({
            thread: undefined,
            comments: [],
            // What the dialog draws, derived from the list every time it is
            // set: the branches the social media answered, computed once
            // instead of once per comment drawn.
            roots: [],
            repliesByRoot: {},
            account_id: this.props.account.raw_value,
            // A publication in flight holds the aim still: the composer that
            // is sending must not be destroyed by a comment taking the aim,
            // because the one that would replace it starts able to send the
            // text the first one has not published yet.
            posting: false,
        });
        onWillStart(async () => {
            this.state.thread = this.threadService.getThread(
                "social.post.account",
                this.props.post.id.value
            );
            const result = await this.socialService.getComments(
                this.props.post.id.raw_value
            );
            if (result && result.success) {
                this.setComments(result.data || []);
            } else {
                this.notificationService.add(
                    (result && result.message) || _t("Error retrieving comments"),
                    {
                        type: "danger",
                    }
                );
            }
        });

        useBus(this.env.bus, "SOCIAL:RELOAD_COMMENTS", async () => {
            await this.updateListComments();
        });

        onMounted(() => {
            this.intervalRefreshComment = setInterval(() => {
                this.updateListComments();
            }, 120000);
        });

        onWillUnmount(() => {
            clearInterval(this.intervalRefreshComment);
            // A target left behind would greet the next dialog with a banner
            // for a comment that is no longer on screen.
            this.socialService.clearReplyTarget();
        });

        useBus(this.busService, "notification", ({detail: notifications}) => {
            if (notifications && notifications.length > 0) {
                notifications.forEach((notif) => {
                    const {payload, type} = notif;
                    if (type !== "comments" || !payload) {
                        return;
                    }
                    // The channel is the partner, so this dialog hears every
                    // comment the user publishes, on this publication or on
                    // any other one open at the same time. Only its own is
                    // acted upon.
                    if (
                        payload.post_account_id !== undefined &&
                        payload.post_account_id !== this.props.post.id.raw_value
                    ) {
                        return;
                    }
                    const message =
                        payload.message === undefined
                            ? _t("Comment created")
                            : payload.message;
                    const typeNotif = payload.success === true ? "success" : "danger";
                    this.notificationService.add(message, {
                        type: typeNotif,
                    });
                    if (payload.success === true) {
                        this.lastReplyTarget = null;
                        // The comment the social media answered is drawn from
                        // what it already said, and only a connector that
                        // could not shape it costs a second read of the
                        // thread.
                        if (!this.insertComment(payload.comment)) {
                            this.env.bus.trigger("SOCIAL:RELOAD_COMMENTS");
                        }
                    } else {
                        this.restoreReplyTarget();
                        // Reading the comments of a publication the social
                        // media just reported as gone would only fail again,
                        // so the dialog closes instead of reloading them.
                        if (!payload.post_deleted) {
                            this.env.bus.trigger("SOCIAL:RELOAD_COMMENTS");
                        }
                    }
                    this.env.bus.trigger("SOCIAL:RELOAD_ORGANIZATION", {
                        account_id: this.props.account.raw_value,
                        post_id: this.props.post.remote_ref.raw_value,
                    });
                    if (payload.post_deleted) {
                        this.props.close();
                    }
                });
            }
        });
    }

    /**
     * Keep the comments and the branches they draw, in one traversal.
     *
     * The list is what the social media answered and the dialog draws it in
     * that order, so the branches are built by walking it once instead of
     * grouping it: the roots come out in the order they were answered, and so
     * do the replies of each of them.
     *
     * @param {Object[]} comments The comments the social media answered.
     */
    setComments(comments) {
        const byRef = new Map(comments.map((comment) => [comment.remote_ref, comment]));
        const rootByRef = new Map();
        const roots = [];
        const repliesByRoot = {};
        for (const comment of comments) {
            const rootRef = this.rootRefOf(comment, byRef, rootByRef);
            if (rootRef === comment.remote_ref) {
                roots.push(comment);
                repliesByRoot[rootRef] = repliesByRoot[rootRef] || [];
            } else {
                repliesByRoot[rootRef] = repliesByRoot[rootRef] || [];
                repliesByRoot[rootRef].push(comment);
            }
        }
        this.state.comments = comments;
        this.state.roots = roots;
        this.state.repliesByRoot = repliesByRoot;
    }

    /**
     * The first-level comment a comment ends up hanging from.
     *
     * X answers the whole conversation, replies of replies included, and
     * those are drawn under the comment that started the branch instead of
     * one level deeper: LinkedIn does not nest beyond one level and offering
     * a third one on X alone is the asymmetry this avoids. A comment whose
     * parent is not in the list — the reference did not travel, or the parent
     * is the publication — is a first-level one and answers for itself.
     *
     * @param {Object} comment The comment being placed.
     * @param {Map} byRef The comments of the list by remote reference.
     * @param {Map} rootByRef The roots already resolved, filled as the list
     *     is walked. A chain that closes on itself is left out of it: a
     *     ``parent_ref`` pointing backwards answers a different root
     *     depending on where the walk started, so caching one of them would
     *     answer for the others.
     * @returns {String} The reference of the comment that starts its branch.
     */
    rootRefOf(comment, byRef, rootByRef) {
        const walked = [];
        const seen = new Set();
        let current = comment;
        while (current.parent_ref && byRef.has(current.parent_ref)) {
            if (rootByRef.has(current.remote_ref)) {
                const known = rootByRef.get(current.remote_ref);
                walked.forEach((ref) => rootByRef.set(ref, known));
                return known;
            }
            if (seen.has(current.remote_ref)) {
                return current.remote_ref;
            }
            seen.add(current.remote_ref);
            walked.push(current.remote_ref);
            current = byRef.get(current.parent_ref);
        }
        walked.forEach((ref) => rootByRef.set(ref, current.remote_ref));
        return current.remote_ref;
    }

    /** The comments hanging from the publication. */
    get comments() {
        return this.state.roots;
    }

    repliesOf(comment) {
        return this.state.repliesByRoot[comment.remote_ref] || [];
    }

    onShowAllImages(ev) {
        ev.stopPropagation();
        this.dialogService.add(SocialImageDialog, {
            title: _t("All Images"),
            images: JSON.parse(this.props.post.image_urls.raw_value),
        });
    }

    async updateListComments() {
        const result = await this.socialService.getComments(
            this.props.post.id.raw_value
        );
        // A refresh that could not be read says nothing about the comments
        // already on screen: emptying the list would carry away the comment
        // being answered, and with it the composer holding the reply.
        if (!result?.success) {
            return;
        }
        this.setComments(result.data || []);
    }

    onPostingChange(posting) {
        this.state.posting = posting;
    }

    /**
     * Give the composer back once the comment has left the browser.
     *
     * This is `onPostCallback` of `mail`, which core fires inside the branch
     * that publishes, after the request resolved and before the composer is
     * emptied. Neither the empty body, nor the attachment still uploading,
     * nor a re-entrant send reach it, and a request that failed throws before
     * it — so the aim is only given up by a comment that was really sent.
     * `mail` cancels its own reply target at that very point
     * (`@mail/core/common/composer` `_sendMessage`).
     */
    onCommentPosted() {
        this.lastReplyTarget = this.socialState.replyTarget
            ? {...this.socialState.replyTarget}
            : null;
        this.socialService.clearReplyTarget();
    }

    /**
     * Aim again at the comment the rejected reply was answering.
     *
     * The text is gone either way —the browser is told the request went
     * through, and the social media only reports the rejection afterwards
     * through the bus, once `mail` has already emptied the composer— but the
     * aim does not have to be: the retry starts under the same comment.
     */
    restoreReplyTarget() {
        if (!this.lastReplyTarget) {
            return;
        }
        this.socialService.setReplyTarget(
            this.lastReplyTarget.commentRef,
            this.lastReplyTarget.actorLabel
        );
        this.lastReplyTarget = null;
    }

    /**
     * Draw the comment the social media has just created.
     *
     * The connector answers it already shaped, so the thread is not read
     * again for something the social media said in the same breath as the
     * creation. A connector whose social media does not say enough answers
     * nothing here, and then the caller falls back to rereading.
     *
     * @param {Object} comment The comment as `get_comments` shapes them.
     * @returns {Boolean} Whether it could be drawn from what arrived.
     */
    insertComment(comment) {
        if (!comment || !comment.remote_ref) {
            return false;
        }
        if (
            this.state.comments.some((known) => known.remote_ref === comment.remote_ref)
        ) {
            return true;
        }
        this.setComments([...this.state.comments, comment]);
        if (comment.parent_ref) {
            // A folded branch would hide the reply that was just published,
            // which is the one thing the user is looking for.
            this.env.bus.trigger("SOCIAL:REPLY_PUBLISHED", {
                parentRef: comment.parent_ref,
            });
        }
        return true;
    }

    /** Whether the composer of this social media takes an attachment. */
    get commentAllowUpload() {
        return true;
    }

    /**
     * The comment being answered, while it is one of the comments on screen.
     *
     * This is where the composer goes, not whether a reply is being written:
     * a target the list no longer holds — the comment was deleted, or X
     * turned it into a reply — has no comment to sit under, and the composer
     * stays at the head of the dialog answering it from there.
     */
    get activeReplyTarget() {
        const target = this.socialState.replyTarget;
        if (!target) {
            return null;
        }
        return this.comments.some((comment) => comment.remote_ref === target.commentRef)
            ? target
            : null;
    }

    /**
     * The comment is published on the social media, not logged as a note.
     *
     * A reply is written under the comment it answers, so this composer says
     * whom it comments as. It also stands in for the one under the comment
     * when the aimed comment is not on the list — the social media stopped
     * serving it, or X turned it into a reply — and then it is a reply that
     * is being written here: the social media does not always give the name
     * of who wrote it, LinkedIn answers a URN, and a banner naming nobody
     * says less than the placeholder.
     */
    get composerPlaceholder() {
        if (this.socialState.replyTarget) {
            return _t("Write your reply…");
        }
        const account = this.record.author?.value || this.props.account.value;
        return _t("Comment as %(account)s…", {account});
    }

    get renderingContext() {
        return {
            luxon,
            record: this.record,
            images: this.props.images,
            isDialog: true,
            onShowAllImages: this.onShowAllImages.bind(this),
        };
    }
}
