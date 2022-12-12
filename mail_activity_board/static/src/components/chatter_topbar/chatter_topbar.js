/* Copyright 2018 David Juaneda
 * Copyright 2021 Sodexis
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
    }
);
