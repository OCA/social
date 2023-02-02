/** @odoo-module **/
import {ChatterTopbar} from "@mail/components/chatter_topbar/chatter_topbar";
import {patch} from "web.utils";
const components = {ChatterTopbar};
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
        _onListActivity(ev) {
            var self = this;
            rpc.query({
                model: this.chatter.thread.model,
                method: "redirect_to_activities",
                args: [[]],
                kwargs: {
                    id: this.chatter.thread.id,
                    model: this.chatter.thread.model,
                },
                context: {},
            }).then(function (action) {
                self.env.bus.trigger("do-action", {
                    action,
                    options: {
                        on_close: () => {
                            this.chatter.thread.refreshActivities();
                            this.chatter.thread.refresh();
                        },
                    },
                });
            });
        },
    }
);
