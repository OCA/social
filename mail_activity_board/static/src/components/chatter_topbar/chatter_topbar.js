/* Copyright 2018 David Juaneda
 * License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl). */
odoo.define(
    "mail_activity_board/static/src/components/chatter_topbar/chatter_topbar.js",
    function (require) {
        "use strict";

        var rpc = require("web.rpc");

        const components = {
            ChatterTopbar: require("mail/static/src/components/chatter_topbar/chatter_topbar.js"),
        };

        const {patch} = require("web.utils");

        patch(
            components.ChatterTopbar,
            "mail_activity_board/static/src/components/chatter_topbar/chatter_topbar.js",
            {
                // --------------------------------------------------------------------------
                // Handlers
                // --------------------------------------------------------------------------

                /**
                 * @private
                 * @param {MouseEvent} ev
                 */
                _onListActivity(ev) {
                    console.log("test");
                    console.log(this.chatter);
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
    }
);
