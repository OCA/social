// Copyright 2019 Therp BV <https://therp.nl>
// License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
odoo.define('mass_mailing_template_email.editor', function (require) {
    "use strict";
    var snippets_editor = require('web_editor.snippet.editor');

    snippets_editor.Class.include({
        compute_snippet_templates: function (html) {
            this._super(html);
            this.$('.o_mass_mailing_themes_upgrade').remove();
        },
    });
});
