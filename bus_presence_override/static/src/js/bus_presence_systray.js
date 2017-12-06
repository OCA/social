/* Copyright 2017 LasLabs Inc.
   License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl). */

odoo.define('bus_presence_systray', function (require) {
    "use strict";

    var Bus = require('bus.bus').bus;
    var DataModel = require('web.DataModel');
    var Session = require('web.session');
    var SystrayMenu = require('web.SystrayMenu');
    var Widget = require('web.Widget');
    var Qweb = require('web.core').qweb;
    var LocalStorage = require('web.local_storage');

    function on(type, listener) {
        if (window.addEventListener) {
            window.addEventListener(type, listener);
        } else {
            // IE8
            window.attachEvent('on' + type, listener);
        }
    }

    var BusPresenceSystray = Widget.extend({
        template: 'bus_presence_systray',
        events: {
            'click .o-user-status-select': 'onClickUserStatusSelect',
        },
        init: function() {
            this._super.apply(this, arguments);
            this.resPartnerMod = new DataModel('res.partner');
            this.busPresenceMod = new DataModel('bus.presence');
            Bus.on('notification', this, _.throttle(this.notificationsUpdateCurrentUserStatus.bind(this), 100, {leading: false}));
            on('storage', this.onStorage.bind(this));
        },
        start: function () {
            this.startDetermineUserStatus();
            Bus.start_polling();
            return this._super();
        },
        startDetermineUserStatus: function () {
            if (Bus.is_master === true) {
                this.writeBusPresenceStatus('online');
                this.updateUserStatusIcon('online');
                LocalStorage.setItem('user.partner_im_status', 'online');
            } else {
                var statusVal = LocalStorage.getItem('user.partner_im_status');
                this.updateUserStatusIcon(statusVal);
            }
        },
        onStorage: function (event) {
            if (event.key === 'user.partner_im_status') {
                this.updateUserStatusIcon(event.newValue);
            }
        },
        notificationsUpdateCurrentUserStatus: function (notifications) {
            _.each(notifications, $.proxy(
                function (notification) {
                    var model = notification[0][1];
                    var partnerId = notification[1].id;
                    if (model === 'bus.presence' && partnerId === Session.partner_id) {
                        var status = notification[1].im_status;
                        this.updateUserStatusIcon(status);
                        LocalStorage.setItem('user.partner_im_status', status);
                    }
                }, this)
            );
        },
        queryUpdateCurrentUserStatus: function () {
            this.resPartnerMod.query(['im_status'])
                              .filter([['id', '=', Session.partner_id]])
                              .first()
                              .then($.proxy(
                                  function (result) {
                                      this.updateUserStatusIcon(result.im_status);
                                      LocalStorage.setItem('user.partner_im_status', status);
                                  }, this)
                            );
        },
        updateUserStatusIcon: function (status) {
            var options = {'status': status};
            var $icon = this.$('.o-user-systray-status');
            $icon.empty().append($(Qweb.render('mail.chat.UserStatus', options)));
        },
        onClickUserStatusSelect: function (event) {
            var status = $(event.currentTarget).attr('name');
            this.updateUserStatusIcon(status);
            this.writeBusPresenceStatus(status);
            LocalStorage.setItem('user.partner_im_status', status);
        },
        writeBusPresenceStatus: function (status) {
            this.busPresenceMod.query(['id'])
                               .filter([['partner_id', '=', Session.partner_id]])
                               .first()
                               .then($.proxy(
                                    function (result) {
                                        this.busPresenceMod.call('write', [[result.id], {'status': status}]);
                                    }, this)
                               );
        },
    });

    SystrayMenu.Items.push(BusPresenceSystray);

});

