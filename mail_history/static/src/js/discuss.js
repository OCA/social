/* Copyright 2020 Tecnativa - Carlos Roca
   License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html). */
odoo.define('mail_history.Discuss', function (require) {
    "use strict";

    var Discuss = require('mail.Discuss');
    var core = require('web.core');

    var QWeb = core.qweb;

    Discuss.include({

        /**
         * Render 'history' mailbox menu entry in Discuss
         *
         * @private
         * @returns {jQueryElementt}
         */
        _renderSidebar: function () {
            var $sidebar = this._super.apply(this, arguments);
            // Because Odoo implementation isn't designed to be inherited
            // properly, we inject 'history' button using jQuery.
            var $history_item = $(QWeb.render('mail_history.SidebarHistory',
                {activeThreadID:
                    this._thread ? this._thread.getID() : undefined}));
            $history_item.insertAfter(
                $sidebar.find(".o_mail_discuss_title_main").filter(":last"));
            return $sidebar;
        },
    });
});
