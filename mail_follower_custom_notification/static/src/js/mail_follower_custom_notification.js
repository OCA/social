//-*- coding: utf-8 -*-
//© 2015 Therp BV <http://therp.nl>
//License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

openerp.mail_follower_custom_notification = function(instance)
{
    instance.mail_followers.Followers.include({
        display_subtypes: function(data, id, dialog)
        {
            var $list = this.$('.oe_subtype_list ul');
            if (dialog)
            {
                $list = this.$dialog.$el;
            }
            $list.empty();
            this._super(data, id, dialog);
            $list.find('input[type=checkbox]').change(function()
            {
                $list.find(_.str.sprintf(
                    '#custom_notification_%s%s',
                    jQuery(this).data('id'),
                    dialog ? '_dialog' : ''
                ))
                .toggle(jQuery(this).prop('checked'));
            });
            if(!dialog)
            {
                $list.find('.oe_custom_notification input[type=radio]')
                .change(this.proxy('do_update_subscription'));
            };
        },
        do_update_subscription: function(event, user_pid)
        {
            /*
            if(jQuery(event.currentTarget).parents('.oe_custom_notification')
               .length)
            {
                // mail reacts on all inputs, suppress for our inputs
                return jQuery.when();
            }
            */
            var self = this,
                update_func = 'message_custom_notification_update_user',
                follower_ids = [this.session.uid],
                custom_notifications = {},
                oe_action = this.$('.oe_actions');
            if(user_pid)
            {
                update_func = 'message_custom_notification_update';
                follower_ids = [user_pid];
                oe_action = jQuery('.oe_edit_actions');
            }
            _(follower_ids).each(function(follower)
            {

                var follower_settings = custom_notifications[follower] = {};
                oe_action.find('.oe_custom_notification')
                .each(function()
                {
                    var id = parseInt(jQuery(this).data('id')),
                        settings = follower_settings[id] = {};
                    settings['force_mail'] = jQuery(this)
                        .find('.oe_custom_notification_mail input:checked')
                        .val();
                    settings['force_own'] = jQuery(this)
                        .find('.oe_custom_notification_own input:checked')
                        .val();
                });
            });
            return jQuery.when(this._super.apply(this, arguments))
            .then(function()
            {
                return self.ds_model.call(
                    update_func,
                    [[self.view.datarecord.id], custom_notifications])
            })
        },
    });
}
