/* © 2014-2015 Grupo ESOC <http://www.grupoesoc.es>
 * License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
 */

openerp.mail_full_expand = function (instance) {
    instance.mail.ThreadMessage.include({
        bind_events: function () {
            this._super.apply(this, arguments);
            this.$('.oe_full_expand').on('click', this.on_message_full_expand);
        },

        on_message_full_expand: function() {
            // Get the action data and execute it to open the full view
            var do_action = this.do_action,
                msg_id = this.id;

            this.rpc("/web/action/load", {
                "action_id": "mail_full_expand.act_window",
            })
            .done(function(action) {
                action.res_id = msg_id;
                do_action(action);
            });
        }
    });
};
