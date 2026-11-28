/** @odoo-module **/

import {Component, onMounted, useState} from "@odoo/owl";
import {Dialog} from "@web/core/dialog/dialog";
import {ConfirmationDialog} from "@web/core/confirmation_dialog/confirmation_dialog";
import {useService} from "@web/core/utils/hooks";
import {_t} from "@web/core/l10n/translation";

// Odoo 19 exposes luxon as a global, not as a module.
const {DateTime} = window.luxon;

/**
 * Comments of a publication, read and written on the social media.
 *
 * The dialog asks the connector of the publication for the comments every
 * time it opens: what Odoo stores is the count, not the comments themselves,
 * so reading them is always a call to the social media.
 */
export class SocialCommentsDialog extends Component {
    static template = "social_media_base.SocialCommentsDialog";
    static components = {Dialog};
    static props = {
        postAccountId: {type: Number, required: true},
        title: {type: String, optional: true},
        close: {type: Function, optional: true},
    };

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.dialog = useService("dialog");
        this.state = useState({
            loading: true,
            sending: false,
            comments: [],
            error: "",
            body: "",
        });
        // The comments come from the social media, which may take seconds to
        // answer: loading them after the first paint is what shows the dialog
        // (and its spinner) instead of a button that seems to do nothing.
        onMounted(() => this.loadComments());
    }

    get dialogTitle() {
        return this.props.title || _t("Comments");
    }

    /**
     * The useful text of a failed call.
     *
     * An ``RPCError`` carries "Odoo Server Error" in ``message``; the reason
     * the server answered with is in ``data.message``.
     *
     * @param {Error} error
     * @returns {String}
     */
    errorMessage(error) {
        return (
            (error && error.data && error.data.message) ||
            (error && error.message) ||
            _t("The comments could not be read.")
        );
    }

    formatCommentDate(value) {
        if (!value) {
            return "";
        }
        const date = DateTime.fromISO(value).isValid
            ? DateTime.fromISO(value)
            : DateTime.fromSQL(value);
        return date.isValid ? date.toLocaleString(DateTime.DATETIME_SHORT) : value;
    }

    async loadComments() {
        this.state.loading = true;
        this.state.error = "";
        try {
            const result = await this.orm.call("social.post.account", "get_comments", [
                this.props.postAccountId,
            ]);
            if (result && result.success) {
                this.state.comments = result.data || [];
            } else {
                this.state.comments = [];
                this.state.error =
                    (result && result.message) || _t("The comments could not be read.");
            }
        } catch (error) {
            this.state.comments = [];
            this.state.error = this.errorMessage(error);
        } finally {
            this.state.loading = false;
        }
    }

    async sendComment() {
        const body = this.state.body.trim();
        if (!body || this.state.sending) {
            return;
        }
        this.state.sending = true;
        try {
            const result = await this.orm.call(
                "social.post.account",
                "create_comment",
                [this.props.postAccountId, {body}]
            );
            if (result && result.success) {
                this.state.body = "";
                await this.loadComments();
            } else {
                this.notification.add(
                    (result && result.message) ||
                        _t("The comment could not be published."),
                    {type: "danger"}
                );
            }
        } catch (error) {
            this.notification.add(error.message || String(error), {
                type: "danger",
            });
        } finally {
            this.state.sending = false;
        }
    }

    async deleteComment(comment) {
        this.dialog.add(ConfirmationDialog, {
            body: _t("Delete this comment from the social media?"),
            confirmLabel: _t("Delete"),
            confirm: () => this._deleteComment(comment),
        });
    }

    async _deleteComment(comment) {
        try {
            const result = await this.orm.call(
                "social.post.account",
                "delete_comment",
                [this.props.postAccountId, comment.id]
            );
            if (result && result.success) {
                await this.loadComments();
            } else {
                this.notification.add(
                    (result && result.message) ||
                        _t("The comment could not be deleted."),
                    {type: "danger"}
                );
            }
        } catch (error) {
            this.notification.add(this.errorMessage(error), {
                type: "danger",
            });
        }
    }
}
