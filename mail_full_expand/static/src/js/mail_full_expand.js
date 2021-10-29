/* Copyright 2014-2015 Grupo ESOC <http://www.grupoesoc.es>
 * License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
 */
odoo.define(
    "mail_full_expand/static/src/components/message/mail_full_expand.js",
    function (require) {
        "use strict";

        const components = {
            Message: require("mail/static/src/components/message/message.js"),
        };
        const {patch} = require("web.utils");

        patch(components.Message, "mail_full_expand.main", {
            async _onClickMessageFullExpand(ev) {
                ev.stopPropagation();
                const action = await this.rpc({
                    route: "/web/action/load",
                    params: {action_id: "mail_full_expand.mail_message_action"},
                });
                action.res_id = this.message.id;
                this.env.bus.trigger("do-action", {action: action});
            },
        });
    }
);
