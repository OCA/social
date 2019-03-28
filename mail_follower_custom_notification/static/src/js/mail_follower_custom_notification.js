// -*- coding: utf-8 -*-
// Copyright 2015-2019 Therp BV <http://therp.nl>
// License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
odoo.define('mail_follower_custom_notification', function(require) {
    'use strict';
    var core = require('web.core');
    require('mail.Followers');
    core.form_widget_registry.get('mail_followers').include({
        /* eslint-disable-next-line no-unused-vars */
        display_subtypes:function (data, dialog, display_warning) {
            this._super.apply(this, arguments);
            var $list = this.$('ul.o_followers_list');
            if (dialog) {
                $list = this.dialog.$('ul');
            }
            $list.find('input[type=checkbox]').change(function() {
                $list.find(_.str.sprintf(
                    '#custom_notification_%s%s',
                    jQuery(this).data('id'),
                    dialog ? '_dialog' : ''
                )).toggle(jQuery(this).prop('checked'));
            });
            if (!dialog) {
                $list.find(
                    '.oe_custom_notification input[type=radio]'
                ).change(this.proxy('do_update_subscription'));
            }
        },
        /* eslint-disable-next-line no-unused-vars */
        do_update_subscription: function (event, follower_id, is_channel) {
            var self = this,
                update_func = 'message_custom_notification_update_user',
                follower_ids = [this.session.uid],
                custom_notifications = {},
                $list = this.$('ul');
            if (follower_id !== undefined) {
                update_func = 'message_custom_notification_update';
                follower_ids = [follower_id];
                $list = this.dialog.$('ul');
            }
            _(follower_ids).each(function(follower) {
                var follower_settings = custom_notifications[follower] = {};
                $list.find(
                    '.o_mail_follower_custom_notification'
                ).each(function () {
                    var id = parseInt(jQuery(this).data('id'), 10),
                        settings = follower_settings[id] = {};
                    settings.force_mail = jQuery(this)
                        .find('.mail input:checked')
                        .val();
                    settings.force_own = jQuery(this)
                        .find('.own input:checked')
                        .val();
                });
            });
            return jQuery.when(
                this._super.apply(this, arguments)
            ).then(function () {
                return self.ds_model.call(
                    update_func,
                    [[self.view.datarecord.id], custom_notifications]);
            }).then(this.proxy('render_value'));
        },
    });
});
