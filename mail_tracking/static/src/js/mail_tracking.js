/* © 2016 Antonio Espinosa - <antonio.espinosa@tecnativa.com>
     License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html). */

(function ($, window, document) {
    'use strict';

    openerp.mail_tracking = function (instance) {
        var _t = instance.web._t,
            _lt = instance.web._lt;
        var QWeb = instance.web.qweb;
        var mail_orig = instance.mail;
        var mail_inherit = function() {
            instance.mail.MessageCommon.include({
                init: function (parent, datasets, options) {
                    this._super(parent, datasets, options);
                    this.partner_trackings = datasets.partner_trackings || [];
                }
            });
            instance.mail.ThreadMessage.include({
                bind_events: function () {
                    this._super();
                    this.$('.oe_mail_action_tracking').on('click', this.on_tracking_status_clicked);
                },
                on_tracking_status_clicked: function (event) {
                    event.preventDefault();
                    var tracking_email_id = $(event.delegateTarget).data('tracking');
                    var state = {
                        'model': 'mail.tracking.email',
                        'id': tracking_email_id,
                        'title': _t("Message tracking"),
                    };
                    instance.webclient.action_manager.do_push_state(state);
                    console.log('tracking_email_id = ' + tracking_email_id);
                    var action = {
                        type:'ir.actions.act_window',
                        view_type: 'form',
                        view_mode: 'form',
                        res_model: 'mail.tracking.email',
                        views: [[false, 'form']],
                        target: 'new',
                        res_id: tracking_email_id,
                    };
                    this.do_action(action);
                }
            });
        };

        // Tricky way to guarantee that this module is loaded always
        // after mail module.
        // When --load=web,mail_tracking is specified in init script, then
        // web and mail_tracking are the first modules to load in JS
        if (instance.mail.MessageCommon === undefined) {
            instance.mail = function(instance) {
                instance.mail = mail_orig;
                instance.mail(instance, instance.mail);
                mail_inherit();
            };
        } else {
            mail_inherit();
        }
    };

}(window.jQuery, window, document));
