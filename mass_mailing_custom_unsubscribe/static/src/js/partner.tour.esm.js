/** @odoo-module **/

/* Copyright 2016 Jairo Llopis <jairo.llopis@tecnativa.com>
 * License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl). */

import tour from "web_tour.tour";

// Allow to know if an element is required
$.extend($.expr[":"], {
    propRequired: (element) => $(element).prop("required"),
});

tour.register(
    "mass_mailing_custom_unsubscribe_tour_partner",
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
                ":contains('successfully unsubscribed')",
        },
    ]
);
