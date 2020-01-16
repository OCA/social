/* Copyright 2020 Creu Blanca
     License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html). */

odoo.define('mail_private.composer', function (require) {
    "use strict";
    var ChatterComposer = require('mail.ChatterComposer');

    ChatterComposer.include({
        init: function (parent, model, suggested_partners, options) {
            this._super(parent, model, suggested_partners, options);
            _.extend(this.events, {
                'click .o_composer_button_send_private': 'on_send_private',
            });
            this.options.allow_private =
                parent.record.data.allow_private || false;
        },
        renderElement: function () {
            var result = this._super.apply(this, arguments);
            if (this.options.allow_private) {
                var self = this;
                this._rpc({
                    model: this.model,
                    method: 'get_message_security_groups',
                    args: [],
                }).then(function (data) {
                    self.security_groups = data;
                    self._update_security_groups();
                });
            }
            return result;
        },
        _get_group_button: function (group) {
            var $button = $('<button>', {
                'class': 'o_dropdown_toggler_btn btn btn-sm ' +
                    'o_composer_button_send_private hidden-xs',
                'type': 'button',
                'data-group-id': group.id,
            });
            if (group.icon) {
                var $icon = $('<i>', {
                    'class': 'o_thread_private_tooltip ' +
                        'o_thread_message_private fa fa-lg ' + group.icon,
                });
                $button.append($icon);
            } else {
                var $data = $('<span>');
                $data.text(group.button_name);
                $button.append($data);
            }
            return $button;
        },
        _update_security_groups: function () {
            var node = this.$el.find('.o_composer_send_private_group');
            var self = this;
            _.each(this.security_groups, function (group) {
                var $button = self._get_group_button(group);
                node.append($button);
            });
        },
        on_send_private: function (event) {
            if (this.is_empty() || !this.do_check_attachment_upload()) {
                return;
            }
            var group_id = event.currentTarget.getAttribute('data-group-id');
            clearTimeout(this.canned_timeout);
            var self = this;
            this.preprocess_message().then(function (message) {
                message.context.default_mail_group_id = group_id;
                self.trigger('post_message', message);
                self.clear_composer_on_send();
                self.$input.focus();
            });
        },
    });

});
