/* Copyright 2016 Jairo Llopis <jairo.llopis@tecnativa.com>
 * Copyright 2016 Vicent Cubells <vicent.cubells@tecnativa.com>
 * License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl). */

odoo.define('openerp.website.snippet.options.fixed_560px', function (require) {
"use strict";

var core = require('web.core');
var options = require('web_editor.snippets.options');


openerp.website.snippet.options.fixed_560px = openerp.website.snippet.Option.extend({
        // Remove attributes added by Odoo at drop time, to avoid him to try
        // to overwrite the snippet view itself instead of just replacing the
        // email/template body.
        clean_for_save: function () {
            this._super();
            var bad_attrs = [
                "data-oe-field",
                "data-oe-id",
                "data-oe-model",
                "data-oe-source-id",
                "data-oe-xpath",
                "data-original-title",
            ];
            for (var n in bad_attrs) {
                var att = bad_attrs[n];
                this.$target.find("[" + att + "]").removeAttr(att);
            }},
});
});