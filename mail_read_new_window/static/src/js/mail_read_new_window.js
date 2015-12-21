/* © 2015 initOS GmbH (<http://www.initos.com>)
*  License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
*/

openerp.mail_read_new_window = function (instance) {
    var _t = instance.web._t,
       _lt = instance.web._lt;

    instance.mail.ThreadMessage.include({
        bind_events: function(){
            this._super.apply(this, arguments);
            this.$('.oe_mail_open').on('click', this.on_read_new_window)
        },

        on_read_new_window: function(event){
            var self = this;

            var _url =  _.str.sprintf('#id=%s&view_type=form&model=mail.message',
                            this.id);
            var action = {
                name: _t('Open message in new window'),
                type: 'ir.actions.act_url',
                url: _url,
                target: 'new',
            };

            self.do_action(action);
        }
    });
}
