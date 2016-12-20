/* Copyright 2016 Tecnativa - Jairo Llopis
 * Copyright 2016 Tecnativa - Vicent Cubells
 * License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html). */

odoo.define('website_mail_snippet_vertical_resize_base.editor', function (require) {
    "use strict";

var ajax = require('web.ajax');
var core = require('web.core');
var base = require('web_editor.base');
var web_editor = require('web_editor.editor');
var options = require('web_editor.snippets.options');

var _t = core._t;

var editor = options.extend({
    start: function () {
            var self = this;
            self._super();
            return self.$el.find(".js_vertical_resize").click(function(){
                return self.ask();
            });
        },
    ask: function(type, value) {
        var self = this;
        if (type !== "click") return;
        return web_editor.prompt({
                window_title: _t("Set element height"),
                input: _t("Element height in pixels"),
            })
            .done(function (answer) {
                return self.resize(answer);
            });
        },
    resize: function(size) {
        this.$target.css("height", String(size) + "px");

            // Old-school height attribute changed too if needed
            if (this.$target.attr("height")) {
                this.$target.attr("height", size);
            }
    }
});
});
