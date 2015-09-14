/* © 2014-2015 Grupo ESOC <www.grupoesoc.es>
 * License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
 */

openerp.mail_forward = function (instance) {
    var _t = instance.web._t;
    instance.mail.ThreadMessage.include({
        bind_events: function () {
            this._super.apply(this, arguments);
            this.$('.oe_forward').on('click', this.on_message_forward);
        },

        on_message_forward: function () {
            // Generate email subject as possible from record_name and subject
            var subject = ["FWD"];
            if (this.record_name && (this.show_record_name ||
                                     this.parent_id))
            {
                subject.push(this.record_name);
            }
            if (this.subject) {
                subject.push(this.subject);
            } else if (subject.length < 2) {
                subject.push(_t("(No subject)"));
            }

            // Get only ID from the attachments
            var attachment_ids = [];
            for (n in this.attachment_ids) {
                attachment_ids.push(this.attachment_ids[n].id);
            }

            // Get necessary fields from the forwarded message
            var context = {
                default_attachment_ids: attachment_ids,
                default_body:
                    "<p><i>----------" +
                    _t("Forwarded message") +
                    "----------<br/>" +
                    _t("From:") + " " +
                    _.str.escapeHTML(this.author_id[1]) + "<br/>" +
                    _t("Date:") + " " + this.date + "</i></p><br/>" +
                    this.body,
                default_model: this.model,
                default_res_id: this.res_id,
                default_subject: subject.join(": "),
            };

            if (this.model && this.res_id) {
                context.default_destination_object_id =
                    [this.model, this.res_id].join();
            }

            // Get the action data and execute it to open the composer wizard
            var do_action = this.do_action;
            this.rpc("/web/action/load", {
                "action_id": "mail_forward.compose_action",
            })
            .done(function(action) {
                action.context = context;
                do_action(action);
            });
        }
    });
};
