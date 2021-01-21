odoo.define('mail_edit.tour', function (require) {
"use strict";

var core = require('web.core');
var tour = require('web_tour.tour');

var _t = core._t;

tour.register('mail_edit_tour', {
    url: "/web",
}, [tour.STEPS.SHOW_APPS_MENU_ITEM, {
    trigger: '.o_app[data-menu-xmlid="mail.menu_root_discuss"]',
    content: _t('Open Apps -> Discuss menu'),
    position: 'right',
    edition: 'community',
}, {
    trigger: '.o_add[data-type="public"]',
    content: _t("Channels -> Add button"),
    position: 'bottom',
}, {
    trigger: '.o_mail_add_thread[data-type="public"]',
    content: _t("Add a new Channel"),
    position: 'right',
    run: function (actions) {
        actions.text("Mail-Edit Channel", this.$anchor.find("input"));
    },
}, {
    trigger: ".ui-menu-item > a",
    auto: true,
    in_modal: false,
}, {
    trigger: '.o_composer_text_field',
    content: _t("Add some text message to the composer chat box"),
    position: "bottom",
    run: function (actions) {
        actions.text("Sample Message to be edited & Deleted!", this.$anchor);
    },
}, {
    trigger: '.o_composer_send > button',
    extra_trigger: '.o_composer_button_send',
    content: _t("Post your message on the thread"),
    position: "bottom",
}, {
    trigger: '.o_mail_edit',
    content: _t("Click the Edit Icon"),
    position: "bottom",
}, {
    trigger: "input[name=subject]",
    content: _t("Edit Mail Subject"),
    run: "text New Subject",
}, {
    trigger: 'button span:contains(Save)',
    extra_trigger: '.modal-footer',
    content: _t("Save Changes"),
    run: 'click',
}, {
    trigger: '.o_mail_delete:last',
    content: _t("Click the Delete Icon on the last message"),
    position: "bottom",
}, {
    trigger: 'button span:contains(Ok)',
    extra_trigger: '.modal-footer',
    content: _t("Confirm Deletion"),
    run: 'click',
}]);

});
