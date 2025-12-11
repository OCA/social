/** @odoo-module */

import {Chatter} from "@mail/core/web/chatter";
import {browser} from "@web/core/browser/browser";
import {patch} from "@web/core/utils/patch";
import {useEffect} from "@odoo/owl";

const CHATTER_VIEW_STORAGE_KEY = "mail_chatter_split.chatterView";

patch(Chatter.prototype, {
    setup() {
        super.setup();
        const storedView = browser.sessionStorage.getItem(CHATTER_VIEW_STORAGE_KEY);
        this.state.chatterView = storedView || "all";
        useEffect(
            (thread, chatterView) => {
                if (thread && chatterView) {
                    thread.chatterViewMode = chatterView;
                }
            },
            () => [this.state.thread, this.state.chatterView]
        );
    },

    /**
     * Switch the chatter view to show all, messages only, logs only, or activities only
     * @param {String} view - 'all', 'messages', 'logs', or 'activities'
     */
    setChatterView(view) {
        this.state.chatterView = view;
        // Persist the chatter view selection to sessionStorage
        browser.sessionStorage.setItem(CHATTER_VIEW_STORAGE_KEY, view);
        if (this.state.thread) {
            this.state.thread.chatterViewMode = view;
        }
    },

    get isViewAll() {
        return this.state.chatterView === "all";
    },

    get isViewMessages() {
        return this.state.chatterView === "messages";
    },

    get isViewLogs() {
        return this.state.chatterView === "logs";
    },

    get isViewActivities() {
        return this.state.chatterView === "activities";
    },
});
