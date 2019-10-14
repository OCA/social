// Copyright 2019 Therp BV <https://therp.nl>
// License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
odoo.define('mail_reference.tour', function (require) {

    var core = require('web.core');
    var tour = require('web_tour.tour');
    var base = require('web_editor.base');

    tour.register('reference', 
        {
            test: true,
            url: "/web?#id=1&view_type=form&model=res.partner",
            wait_for: base.ready(),
        },
        [
            {
                trigger: '.o_chatter_button_new_message',
                run: function () {
                    this.$anchor.click();
                }
            },
            {
                trigger: '.o_composer_text_field',
                run: function () {
                    this.$anchor.val('^admin');
                    this.$anchor.keydown();
                }
            },
            {
                trigger: '.o_mention_name',
                run: function () {
                    this.$anchor.click();
                }
            },
            {
                trigger: '.o_composer_button_send',
                run: function () {
                    this.$anchor.click();
                }
            },
        ]
    );

});
