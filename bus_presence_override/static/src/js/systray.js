/* Copyright 2017 LasLabs Inc.
   License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl). */

odoo.define('bus_presence_override.systray', function (require) {
    "use strict";

    var DataModel = require('web.DataModel');
    var session = require('web.session');
    var SystrayMenu = require('web.SystrayMenu');
    var Widget = require('web.Widget');

    var Systray = Widget.extend({
        template:'systray',
        events: {
            'click .o_user_presence_status': 'on_click_user_presence_status',
        },
        init: function() {
            this._super.apply(this, arguments);
            this.Partners = new DataModel('res.partner');
            this.status_icons = {
                'online': 'fa fa-circle o_user_online',
                'away': 'fa fa-circle o_user_idle',
                'offline': 'fa fa-circle-o',
            }
        },
        start: function () {
            this._update_im_status_custom(status='online');
            return this._super()
        },
        on_click_user_presence_status: function (event) {
            var status = $(event.target).attr('name');
            this._update_im_status_custom(status);
        },
        _get_im_status: function () {
            var self = this;
            this.Partners.query(['im_status'])
                         .filter([['id', '=', session.partner_id]])
                         .first()
                         .then(function (result) {
                             self._update_systray_status_icon(result['im_status']);
            });
        },
        _update_systray_status_icon: function (status) {
            $('#userStatus i').removeClass()
                              .addClass('o_mail_user_status ' + this.status_icons[status]);
        },
        _update_im_status_custom: function (status) {
            var self = this;
            this.Partners.call('write', [[session.partner_id], {'im_status_custom': status}])
                         .then(function () {
                             self._update_systray_status_icon(status);
            });
        },

    });

    SystrayMenu.Items.push(Systray);

});
