/** @odoo-module **/

/* Copyright 2016 Jairo Llopis <jairo.llopis@tecnativa.com>
 * License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl). */

import tour from "web_tour.tour";

// Allow to know if an element is required
$.extend($.expr[":"], {
    propRequired: (element) => $(element).prop("required"),
});

tour.register(
    "mass_mailing_custom_unsubscribe_tour_contact",
    {
        test: true,
    },
    [
        {
            content: "Choose other reason",
            trigger: ".radio:contains('Other reason') :radio:not(:checked)",
            extra_trigger: "#reason_form #custom_div_feedback",
        },
        {
            content: "Switch to not interested reason",
            trigger: '.radio:contains("I\'m not interested") :radio:not(:checked)',
            extra_trigger: "[name='details']:propRequired",
        },
        {
            content: "Unsubscribe",
            trigger: "#reason_form button:submit",
            extra_trigger: "body:not(:has([name='details']:propRequired))",
        },
        {
            content: "Successfully unsubscribed",
            trigger:
                "body:not(:has(#reason_form)) #subscription_info " +
                ":contains('successfully unsubscribed from')",
        },
        {
            content: "Unsubscription reasons are invisible",
            trigger: "#unsubscribe_form:has(#custom_div_feedback:hidden)",
        },
        {
            content: "List 2 is not cross unsubscriptable",
            trigger: "body:not(:has(li:contains('test list 2')))",
        },
        {
            content: "List 3 is not public",
            trigger: "body:not(:has(li:contains('test list 3')))",
        },
        {
            content: "Uncheck list 1",
            trigger: "li:contains('test list 1') input:checked",
        },
        {
            content: "Choose other reason",
            trigger: ".radio:contains('Other reason') :radio",
            extra_trigger: ".radio:contains('Other reason') :radio:not(:checked)",
        },
        {
            content: "Add details to reason",
            trigger: "[name='details']:visible:propRequired",
            run: "text I want to unsubscribe because I want. Period.",
            extra_trigger: ".radio:contains('Other reason') :radio:checked",
        },
        {
            content: "Update subscriptions 2nd time",
            trigger: "#unsubscribe_form :submit",
        },
        {
            content: "Successfully unsubscribed",
            trigger: "#subscription_info:contains('Your changes have been saved.')",
        },
        {
            content: "Subscribe again to list 0",
            trigger:
                "body:not(:has(#unsubscribe_form #custom_div_feedback:visible)):has(.alert-success) li:contains('test list 0') input:not(:checked)",
        },
        {
            content: "Update subscriptions 3nd time",
            trigger:
                "#unsubscribe_form:not(:has(.js_unsubscription_reason:visible)) :submit",
        },
        {
            content: "Successfully subscribed",
            trigger: "#subscription_info:contains('Your changes have been saved.')",
        },
    ]
);
