/** @odoo-module **/

import {Component, useEffect, useRef, useState} from "@odoo/owl";
import {_t} from "@web/core/l10n/translation";

/** Class marking a message that is shown whole instead of cut. */
export const MESSAGE_EXPANDED_CLASS = "o_social_message_expanded";

/**
 * Whether the message does not fit in the lines it is cut to.
 *
 * A clamped block is taller than what it shows, and that is the only way to
 * tell a message that fits from one that was cut: it depends on the width
 * the card or the preview ends up with, not on how long the text is.
 *
 * @param {HTMLElement} element block holding the message.
 * @returns {Boolean}
 */
export function isMessageClamped(element) {
    return element.scrollHeight - element.clientHeight > 1;
}

/**
 * Label of the link that folds or unfolds a message.
 *
 * @param {Boolean} expanded whether the message is shown whole.
 * @returns {String}
 */
export function messageToggleLabel(expanded) {
    // No leading dots: the cut is drawn by the browser, which already ends
    // the last line it shows with an ellipsis.
    return expanded ? _t("see less") : _t("see more");
}

/**
 * Message of a post, cut to a fixed number of lines.
 *
 * The cut is done by lines and not by characters: a post is written in
 * paragraphs, so the same amount of characters takes a different height
 * depending on how many line breaks it carries, and cards of the same row
 * would still come out uneven. Clamping to lines is what makes every card
 * take the same height whatever the text is.
 *
 * The link is only drawn when the text really does not fit: whether it does
 * depends on the width the card ends up with, so it is measured on the
 * rendered element instead of being guessed from the length of the message.
 */
export class SocialMessage extends Component {
    setup() {
        this.textRef = useRef("text");
        this.state = useState({expanded: false, overflowing: false});

        useEffect(
            (element) => {
                // Measured only while clamped: once expanded the element is
                // as tall as its content and there is nothing left to
                // compare, which would drop the link the user needs to fold
                // the message back.
                if (element && !this.state.expanded) {
                    this.state.overflowing = isMessageClamped(element);
                }
            },
            () => [this.textRef.el, this.props.text, this.state.expanded]
        );
    }

    get expandedClass() {
        return MESSAGE_EXPANDED_CLASS;
    }

    get toggleLabel() {
        return messageToggleLabel(this.state.expanded);
    }

    /**
     * Fold or unfold the message.
     *
     * The click is stopped: these cards open their record on a global
     * click, and reading the whole text is not asking for that.
     *
     * @param {MouseEvent} ev
     */
    onToggle(ev) {
        ev.stopPropagation();
        this.state.expanded = !this.state.expanded;
    }
}

SocialMessage.template = "social_media_base.SocialMessage";
SocialMessage.props = {
    text: {type: String, optional: true},
    lines: {type: Number, optional: true},
    className: {type: String, optional: true},
};
SocialMessage.defaultProps = {
    text: "",
    lines: 6,
    className: "",
};
