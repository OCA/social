/* Copyright 2016 Jairo Llopis <jairo.llopis@tecnativa.com>
 * License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl). */
odoo.define("mass_mailing_custom_unsubscribe.contact_tour",
            function (require) {
    "use strict";
    var base = require("web_editor.base");
    var tour = require("web_tour.tour");
    require("mass_mailing_custom_unsubscribe.require_details");
    require("mass_mailing_custom_unsubscribe.unsubscribe");

    // Allow to know if an element is required
    $.extend($.expr[':'], {
        propRequired: function(element, index, matches) {
           return $(element).prop("required");
        },
    });

    tour.register(
        "mass_mailing_custom_unsubscribe_tour_contact",
        {
            tour: true,
            wait_for: base.ready(),
        },
        [
            {
                content: "Unsubscription reasons are invisible",
                trigger: "#unsubscribe_form:has(.js_unsubscription_reason:hidden)",
            },
            {
                content: "Uncheck list 0",
                trigger: "li:contains('test list 0') input",
                // List 2 is not cross unsubscriptable
                extra_trigger: "body:not(:has(li:contains('test list 2'))) li:contains('test list 0') input:checked",
            },
            {
                content: "Uncheck list 1",
                trigger: "li:contains('test list 1') input:checked",
                extra_trigger: ".js_unsubscription_reason:visible",
            },
            {
                content: "Choose other reason",
                trigger: ".radio:contains('Other reason') :radio",
                extra_trigger: ".radio:contains('Other reason') " +
                            ":radio:not(:checked)",
            },
            {
                content: "Add details to reason",
                trigger: "[name='details']:visible:propRequired",
                run: "text I want to unsubscribe because I want. Period.",
                extra_trigger: ".radio:contains('Other reason') :radio:checked",
            },
            {
                content: "Update subscriptions 1st time",
                trigger: "#unsubscribe_form :submit",
            },
            {
                content: "Subscribe again to list 0",
                trigger: "body:not(:has(#unsubscribe_form .js_unsubscription_reason:visible)):has(.alert-success, li:contains('test list 0') input:not(:checked))",
                run: function () {
                    // This one will get the success again after next step
                    $(".alert-success").removeClass("alert-success");
                },
            },
            {
                content: "Update subscriptions 2nd time",
                trigger: "#unsubscribe_form:not(:has(.js_unsubscription_reason:visible)) :submit",
            },
            {
                content: "Resuscription was OK",
                trigger: ".alert-success",
            }
        ]
    );
});
