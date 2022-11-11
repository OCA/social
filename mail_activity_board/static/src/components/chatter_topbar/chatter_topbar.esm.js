/** @odoo-module **/
import {ChatterTopbar} from "@mail/components/chatter_topbar/chatter_topbar";
import {bus} from "web.core";
import {patch} from "@web/core/utils/patch";
const components = {ChatterTopbar};
// Import {rpc}
import rpc from "web.rpc";

patch(
    components.ChatterTopbar.prototype,
    "mail_activity_board/static/src/components/chatter_topbar/chatter_topbar.esm.js",
    {
        // --------------------------------------------------------------------------
        // Handlers
        // --------------------------------------------------------------------------

        /**
         * @private
         * @param {MouseEvent} ev
         */
        // eslint-disable-next-line no-unused-vars
        async _onListActivity(ev) {
            rpc.query({
                model: this.chatterTopbar.chatter.thread.model,
                method: "redirect_to_activities",
                args: [[]],
                kwargs: {
                    id: this.chatterTopbar.chatter.thread.id,
                    model: this.chatterTopbar.chatter.thread.model,
                },
                context: {},
            }).then(function (action) {
                bus.trigger("do-action", {
                    action,
                    options: {
                        on_close: () => {
                            this.chatterTopbar.chatter.thread.refreshActivities();
                            this.chatterTopbar.chatter.thread.refresh();
                        },
                    },
                });
            });
        },
    }
);
