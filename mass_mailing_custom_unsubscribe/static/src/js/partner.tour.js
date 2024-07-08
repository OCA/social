/* Copyright 2016 Jairo Llopis <jairo.llopis@tecnativa.com>
 * License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl). */
odoo.define("mass_mailing_custom_unsubscribe.partner_tour", (require) => {
    "use strict";
    const base = require("web_editor.base");
    const tour = require("web_tour.tour");

    // Allow to know if an element is required
    $.extend($.expr[":"], {
        propRequired: (element) => $(element).prop("required"),
    });

    tour.register(
        "mass_mailing_custom_unsubscribe_tour_partner",
        {
            tour: true,
            wait_for: base.ready(),
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
});
