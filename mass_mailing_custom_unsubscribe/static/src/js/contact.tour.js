/* Copyright 2016 Jairo Llopis <jairo.llopis@tecnativa.com>
 * License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl). */
odoo.define("mass_mailing_custom_unsubscribe.contact_tour",
            function (require) {
    "use strict";
    var Tour = require("web.Tour");
    require("mass_mailing_custom_unsubscribe.require_details");
    require("mass_mailing_custom_unsubscribe.unsubscribe");

    // Allow to know if an element is required
    $.extend($.expr[':'], {
       propRequired: function(element, index, matches) {
           return $(element).prop("required");
       },
    });

    Tour.register({
        id: "mass_mailing_custom_unsubscribe_tour_contact",
        name: "Mass mailing contact unsubscribes",
        mode: "test",
        steps: [
            {
                title: "Unsubscription reasons are invisible",
                waitFor: "#unsubscribe_form .js_unsubscription_reason:hidden",
            },
            {
                title: "Uncheck list 0",
                element: "li:contains('test list 0') input",
                waitFor: "li:contains('test list 0') input:checked",
                // List 2 is not cross unsubscriptable
                waitNot: "li:contains('test list 2')",
            },
            {
                title: "Uncheck list 1",
                element: "li:contains('test list 1') input:checked",
                waitFor: ".js_unsubscription_reason:visible",
            },
            {
                title: "Choose other reason",
                element: ".radio:contains('Other reason') :radio",
                waitFor: ".radio:contains('Other reason') " +
                         ":radio:not(:checked)",
            },
            {
                title: "Add details to reason",
                element: "[name='details']:visible:propRequired",
                sampleText: "I want to unsubscribe because I want. Period.",
                waitFor: ".radio:contains('Other reason') :radio:checked",
            },
            {
                title: "Update subscriptions 1st time",
                element: "#unsubscribe_form :submit",
            },
            {
                title: "Subscribe again to list 0",
                element: "li:contains('test list 0') input:not(:checked)",
                waitFor: ".alert-success",
                waitNot: "#unsubscribe_form .js_unsubscription_reason:visible",
                onend: function () {
                    // This one will get the success again after next step
                    $(".alert-success").removeClass("alert-success");
                },
            },
            {
                title: "Update subscriptions 2nd time",
                element: "#unsubscribe_form :submit",
                waitNot: "#unsubscribe_form .js_unsubscription_reason:visible",
            },
            {
                title: "Resuscription was OK",
                waitFor: ".alert-success",
            }
        ]
    });

    return Tour.tours.mass_mailing_custom_unsubscribe_tour_contact;
});
