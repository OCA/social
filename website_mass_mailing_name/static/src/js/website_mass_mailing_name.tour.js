/* © 2016 Jairo Llopis <jairo.llopis@tecnativa.com>
 * License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl). */

"use strict";
(function ($) {
    openerp.Tour.register({
        id: "mass_mailing_partner",
        name: "Insert a newsletter snippet and subscribe",
        path: "/",
        mode: "test",
        steps: [
            {
                title: "Edit the homepage",
                waitFor: "button[data-action=edit]",
                element: "button[data-action=edit]",
            },
            {
                title: "Click on Insert Blocks",
                waitFor: "button[data-action=snippet]",
                element: "button[data-action=snippet]",
            },
            {
                title: "Click on Structure",
                waitFor: "a[href='#snippet_structure']",
                element: "a[href='#snippet_structure']",
            },
            {
                title: "Drag and drop a text snippet",
                waitFor: ".oe_snippet:contains('Text Block'):visible",
                snippet: ".oe_snippet:contains('Text Block')",
            },
            {
                title: "Click on Insert Blocks again",
                waitFor: "#wrap h2:contains('A Great Headline'), \
                          button[data-action=snippet]",
                element: "button[data-action=snippet]",
            },
            {
                title: "Click on Content",
                waitFor: "a[href='#snippet_content']",
                element: "a[href='#snippet_content']",
            },
            {
                title: "Drag and drop a newsletter snippet",
                waitFor: ".oe_snippet:contains('Newsletter'):visible",
                snippet: ".oe_snippet:contains('Newsletter')",
            },
            {
                title: "Let the default mailing list",
                waitFor: ".modal button:contains('Continue'):visible",
                element: ".modal button:contains('Continue'):visible",
            },
            {
                title: "Save changes",
                waitNot: ".modal:visible",
                element: "button[data-action=save]",
            },
            {
                title: "Subscribe Administrator",
                waitFor: "button[data-action=edit]:visible, \
                          .js_subscribe_btn:visible",
                element: ".js_subscribe_btn",
            },
            {
                title: "Open user menu",
                waitFor: ".js_subscribe .alert-success:visible",
                element: "#top_menu span:contains('Administrator')",
            },
            {
                title: "Log out",
                waitFor: ".js_usermenu a:contains('Logout'):visible",
                element: ".js_usermenu a:contains('Logout'):visible",
            },
            {
                title: "Try to subscribe without data",
                waitFor: "#top_menu a[href='/web/login']:visible, \
                          .js_subscribe_btn:visible",
                element: ".js_subscribe_btn",
            },
            {
                title: "Enter a name",
                waitFor: ".js_subscribe.has-error",
                element: ".js_subscribe_name",
                sampleText: "Visitor",
            },
            {
                title: "Try to subscribe without email",
                element: ".js_subscribe_btn",
            },
            {
                title: "Remove the name",
                waitFor: ".js_subscribe.has-error",
                element: ".js_subscribe_name",
                sampleText: "",
            },
            {
                title: "Enter an email",
                element: ".js_subscribe_email",
                sampleText: "example@example.com",
            },
            {
                title: "Try to subscribe without name",
                element: ".js_subscribe_btn",
            },
            {
                title: "Enter the name again",
                waitFor: ".js_subscribe.has-error",
                element: ".js_subscribe_name",
                sampleText: "Visitor",
            },
            {
                title: "Enter a wrong email",
                element: ".js_subscribe_email",
                sampleText: "bad email",
            },
            {
                title: "Try to subscribe with a bad email",
                element: ".js_subscribe_btn",
            },
            {
                title: "Enter the good email",
                waitFor: ".js_subscribe.has-error",
                element: ".js_subscribe_email",
                sampleText: "example@example.com",
            },
            {
                title: "Try to subscribe with good information",
                element: ".js_subscribe_btn",
            },
            // Expect this test to work in v9 when uncommenting this
            // {
            //     title: "Subscription successful",
            //     waitFor: ".js_subscribe:not(.has-error) \
            //               .alert-success:visible",
            // },
        ],
    });
})(jQuery);
