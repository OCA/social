/* Copyright 2016-2017 Jairo Llopis <jairo.llopis@tecnativa.com>
 * License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl). */
odoo.define("website_mass_mailing_name.editor_and_public_tour", function (require) {
    "use strict";
    var base = require("web_editor.base");
    var tour = require("web_tour.tour");

    tour.register(
        "mass_mailing_name_editor_and_public",
        {
            test: true,
            wait_for: base.ready(),
        },
        [
            // Admin edits home page and adds subscription snippet
            {
                content: "Edit the homepage",
                trigger: ".o_menu_systray a[data-action=edit]",
            },
            {
                content: "Drag and drop a text snippet",
                trigger: ".oe_snippet[name='Text block'] .oe_snippet_thumbnail",
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
            // Log out
            {
                content: "Open user menu",
                extra_trigger: ".js_subscribe .alert-success",
                trigger: "#top_menu span:contains('Admin')",
            },
            {
                content: "Logout",
                trigger: "#o_logout",
            },
            // Now use the widget as a random public user
            {
                content: "Try to subscribe without data",
                extra_trigger: "a:contains('Sign in')",
                trigger: ".js_subscribe_btn",
            },
            {
                content: "Enter a name",
                extra_trigger: "div.input-group.js_subscribe",
                trigger: ".js_subscribe_name",
                run: "text Visitor",
            },
            {
                content: "Try to subscribe without email",
                trigger: ".js_subscribe_btn",
            },
            {
                content: "Remove the name",
                extra_trigger: "div.input-group.js_subscribe",
                trigger: ".js_subscribe_name",
                run: function () {
                    $(".js_subscribe_name").val("");
                },
            },
            {
                content: "Enter an email",
                trigger: ".js_subscribe_email",
                run: "text example@example.com",
            },
            {
                content: "Try to subscribe without name",
                trigger: ".js_subscribe_btn",
            },
            {
                content: "Enter the name again",
                extra_trigger: "div.input-group.js_subscribe",
                trigger: ".js_subscribe_name",
                run: "text Visitor",
            },
            {
                content: "Enter a wrong email",
                trigger: ".js_subscribe_email",
                run: "text bad email",
            },
            {
                content: "Try to subscribe with a bad email",
                trigger: ".js_subscribe_btn",
            },
            {
                content: "Enter the good email",
                extra_trigger: "div.input-group.js_subscribe",
                trigger: ".js_subscribe_email",
                run: "text example@example.com",
            },
            {
                content: "Try to subscribe with good information",
                trigger: ".js_subscribe_btn",
            },
            {
                content: "Subscription successful",
                trigger: ".js_subscribe:not(.has-error) .alert-success",
            },
        ]
    );
});
