/* Copyright 2016-2017 Jairo Llopis <jairo.llopis@tecnativa.com>
 * License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl). */
odoo.define("website_mass_mailing_name.editor_tour", function (require) {
    "use strict";
    var base = require("web_editor.base");
    var tour = require("web_tour.tour");

    tour.register(
        "mass_mailing_name_editor",
        {
            test: true,
            wait_for: base.ready(),
        },
        [
            {
                content: "Edit the homepage",
                trigger: ".o_menu_systray a[data-action=edit]",
            },
            {
                content: "Drag and drop a text snippet",
                trigger: ".oe_snippet[name='Text Block'] .oe_snippet_thumbnail",
                run: "drag_and_drop #wrap",
            },
            {
                content: "Drag and drop a newsletter snippet",
                trigger: ".oe_snippet[name='Newsletter'] .oe_snippet_thumbnail",
                run: "drag_and_drop #wrap .s_text_block",
            },
            {
                content: "Let the default mailing list",
                trigger: ".modal-dialog button:contains('Continue')",
            },
            {
                content: "Save changes",
                extra_trigger: "body:not(:has(.modal:visible))",
                trigger: "#web_editor-top-edit button[data-action=save]",
            },
            {
                content: "Subscribe Administrator",
                extra_trigger: "body:not(:has(#web_editor-top-edit))",
                trigger: ".js_subscribe_btn",
            },
            {
                content: "Open user menu",
                extra_trigger: ".js_subscribe .alert-success",
                trigger: "#top_menu span:contains('Administrator')",
            },
        ]
    );
});
