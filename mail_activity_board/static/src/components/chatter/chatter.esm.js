/** @odoo-module **/
import {Chatter} from "@mail/core/web/chatter";
import {patch} from "@web/core/utils/patch";

patch(Chatter.prototype, {
    // --------------------------------------------------------------------------
    // Handlers
    // --------------------------------------------------------------------------

    /**
     * @private
     * @param {MouseEvent} ev
     */
    // eslint-disable-next-line no-unused-vars
    async _onListActivity(ev) {
        if (this.state.thread) {
            const thread = this.state.thread;
            const action = await this.orm.call(
                thread.model,
                "redirect_to_activities",
                [[]],
                {
                    id: this.state.thread.id,
                    model: this.state.thread.model,
                }
            );
            this.action.doAction(action, {
                onClose: () => {
                    thread.refreshActivities();
                    thread.refresh();
                },
            });
        }
    },
});
