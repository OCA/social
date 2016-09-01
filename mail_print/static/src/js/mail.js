openerp.mail_print = function(instance) {
    instance.mail.ThreadMessage.include({

        bind_events: function () {
            this._super();
            this.$('.oe_mail_print').on('click', this.on_mail_print);
        },

        on_mail_print: function (event) {
            event.preventDefault();
            this.session.get_file({
                'url': '/report/download',
                'data': {'data': '["/report/pdf/mail_print.mail_message/' + this.id + '","qweb-pdf"]'}
            });
        }
    });
};