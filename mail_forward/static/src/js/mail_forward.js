/* © 2014-2015 Grupo ESOC <www.grupoesoc.es>
 * License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
 */

"use strict";
openerp.mail_forward = function (instance) {
    var _t = instance.web._t;
    instance.mail.ThreadMessage.include({
        bind_events: function () {
            this._super.apply(this, arguments);
            this.$('.oe_forward').on('click', this.on_message_forward);
        },

        on_message_forward: function () {
            // Generate email subject as possible from record_name and subject
            var subject = [_t("FWD")];
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
            for (var n in this.attachment_ids) {
                attachment_ids.push(this.attachment_ids[n].id);
            }

            // Get necessary fields from the forwarded message
            var header = [
                "----------" + _t("Forwarded message") + "----------",
                _t("From: ") + this.author_id[1],
                _t("Date: ") + this.date,
            ];
            if (this.subject) {
                header.push(_t("Subject: ") + this.subject);
            }
            if (this.email_to) {
                header.push(_t("To: ") + this.email_to);
            }
            if (this.email_cc) {
                header.push(_t("CC: ") + this.email_cc);
            }
            header = header.map(_.str.escapeHTML).join("<br/>")

            var context = {
                default_attachment_ids: attachment_ids,
                default_body:
                    "<p><i>" + header + "</i></p><br/>" +
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
