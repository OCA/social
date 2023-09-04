/** @odoo-module **/

const {reactive, useState} = owl;

// Set reactive object to observe the current state of failed messages.
// This allows re-rendering only non-reviewed failed messages without
// reloading the window after a failed message has been dealt with.
export const store = reactive({
    reviewedMessageIds: new Set(),
    addMessage(item) {
        this.reviewedMessageIds.add(item);
    },
});

export function useStore() {
    return useState(store);
}
