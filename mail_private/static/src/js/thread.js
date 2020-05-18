/* Copyright 2020 Creu Blanca
     License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html). */

odoo.define('mail_private.widget.Thread', function (require) {
    "use strict";

    var ThreadWidget = require('mail.widget.Thread');

    var ThreadWidgetPrivate = ThreadWidget.include({
        events: _.extend(ThreadWidget.prototype.events, {
            'mouseover .o_thread_message_private': '_renderGroupsPopover',
        }),
        _renderGroupsPopover: function (event) {
            var $tooltip = $(event.currentTarget).closest(
                '.o_thread_private_tooltip');
            if (!$tooltip.length) {
                return;
            }
            var message_text = $(event.currentTarget).data('message-text');
            $tooltip.popover({
                html: true,
                boundary: 'viewport',
                placement: 'top',
                trigger: 'hover',
                offset: '0, 1',
                content: message_text,
            }).popover('show');
        },
    });
    return ThreadWidgetPrivate;
});
