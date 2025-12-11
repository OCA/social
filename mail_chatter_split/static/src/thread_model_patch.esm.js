/** @odoo-module */

import {Record} from "@mail/core/common/record";
import {Thread} from "@mail/core/common/thread_model";

import {patch} from "@web/core/utils/patch";

patch(Thread.prototype, {
    update(data) {
        super.update(data);
        if (this.chatterViewMode === undefined) {
            this.chatterViewMode = "all";
        }
    },
});

Thread.prototype.chatterViewMode = Record.attr("all");

Object.defineProperty(Thread.prototype, "displayedMessages", {
    get() {
        const messages = this.nonEmptyMessages;
        if (!this.chatterViewMode || this.chatterViewMode === "all") {
            return messages;
        }
        if (this.chatterViewMode === "messages") {
            return messages.filter((msg) => this._isUserMessage(msg));
        }
        if (this.chatterViewMode === "logs") {
            return messages.filter((msg) => this._isLogMessage(msg));
        }
        if (this.chatterViewMode === "activities") {
            return messages.filter((msg) => this._isActivity(msg));
        }
        return messages;
    },
    configurable: true,
});

/**
 * Check if a message is a user-generated message
 * @param {Object} msg
 * @returns {Boolean}
 */
Thread.prototype._isUserMessage = function (msg) {
    const userTypes = ["comment", "email", "email_outgoing"];
    if (userTypes.includes(msg.type)) {
        return true;
    }
    if (["auto_comment", "user_notification"].includes(msg.type) && !msg.isBodyEmpty) {
        return true;
    }
    return false;
};

/**
 * Check if a message is a system-generated log
 * @param {Object} msg
 * @returns {Boolean}
 */
Thread.prototype._isLogMessage = function (msg) {
    if (msg.type === "notification") {
        return true;
    }
    if (msg.trackingValues && msg.trackingValues.length > 0) {
        return true;
    }
    if (msg.isBodyEmpty && msg.subtype_description) {
        return true;
    }
    return false;
};

/**
 * Check if a message is an activity
 * @param {Object} msg
 * @returns {Boolean}
 */
Thread.prototype._isActivity = function (msg) {
    return (
        msg.type === "user_notification" ||
        (msg.subtype_description && msg.subtype_description.includes("Activity"))
    );
};
