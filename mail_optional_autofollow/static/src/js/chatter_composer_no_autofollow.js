odoo.define('no_autofollow.composer', function (require) {
    "use strict";
    var ChatterComposer = require('mail.composer.Chatter');

    ChatterComposer.include({
        init: function (parent, model, suggested_partners, options) {
            this._super(parent, model, suggested_partners, options);
            this.mail_post_autofollow = this._init_autofollow();
            this.context["mail_post_autofollow"] = this.mail_post_autofollow;
        },
        events: _.extend(ChatterComposer.prototype.events, {
            'click .o_composer_no_autofollow': 'on_autofollow_click',
        }),
        _init_autofollow: function () {
            return Boolean(this.context["mail_post_autofollow"]);
        },
        _get_autofollow: function () {
            return Boolean(this.$('.o_composer_no_autofollow input:checked').length);
        },
        on_autofollow_click: function (event) {
            this.mail_post_autofollow = this._get_autofollow();
            this.context["mail_post_autofollow"] = this.mail_post_autofollow;
        },
    });

});
