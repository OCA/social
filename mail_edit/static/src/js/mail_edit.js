/* © 2014-2017 Sunflower IT <www.sunflowerweb.nl>*/

 odoo.define('mail_edit.mail_edit', function (require) {
"use strict";

    var Message = require('mail.model.Message');
    var ThreadWidget = require('mail.widget.Thread');
    var Dialog = require('web.Dialog');

    ThreadWidget.include({
        events: _.defaults({
            "click .o_mail_edit": "_onClickMessageEdit",
            "click .o_mail_delete": "_onClickMessageDelete",
        }, ThreadWidget.prototype.events),

        _onClickMessageEdit: function(event) {
            var self = this;
            var do_action = self.do_action,
                msg_id = $(event.currentTarget).data('message-id');

            self._rpc({
                route: "/web/action/load",
                params: {
                    action_id: "mail_edit.mail_edit_action",
                },
            })
            .done(function (action) {
                action.res_id = msg_id;
                self.do_action(action, {
                    on_close: function () {
                        location.reload();
                        //self.trigger_up('refresh_on_fly');
                        //this.reload.bind(this)
                        //self.trigger_up('reload', { keepChanges: true });
                         //self.trigger.bind(self, 'need_refresh')
                    },
                });
            });
        },

        _onClickMessageDelete: function(event, options) {
            var self = this;
            event.stopPropagation();
            event.preventDefault();
            var msg_id = $(event.currentTarget).data('message-id');
            Dialog.confirm(
                self,
                _t("Do you really want to delete this message?"), {
                    confirm_callback: function () {
                        return self._rpc({
                            model: 'mail.message',
                            method: 'unlink',
                            args: [[msg_id]],
                        })
                        .then(function() {
                            //self.trigger_up('reload');
                            location.reload();
                        });
                    },
                }
            );

        }

    });

    Message.include({
        init: function (parent, data) {
            this._super.apply(this, arguments);
            this.is_superuser = data.is_superuser || false;
            this.is_author = data.is_author || false;
        },
    });

});
