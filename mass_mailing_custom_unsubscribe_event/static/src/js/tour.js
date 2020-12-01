/* Copyright 2020 Tecnativa - João Marques
 * License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl). */
odoo.define("mass_mailing_custom_unsubscribe_event.tour",
    function (require) {
        "use strict";
        var base = require("web_editor.base");
        var tour = require("web_tour.tour");

        // Allow to know if an element is required
        $.extend($.expr[':'], {
            propRequired: function (element) {
                return $(element).prop("required");
            },
        });

        tour.register(
            "mass_mailing_custom_unsubscribe_event_tour",
            {
                test: true,
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
                    trigger:
                        ".radio:contains(\"I'm not interested\") :radio:not(:checked)",
                    extra_trigger: "[name='details']:propRequired",
                },
                {
                    content: "Unsubscribe",
                    trigger: "#reason_form button:submit",
                    extra_trigger: "body:not(:has([name='details']:propRequired))",
                },
                {
                    content: "Successfully unsubscribed",
                    trigger: "body:not(:has(#reason_form)) #subscription_info " +
                         ":contains('successfully unsubscribed')",
                },
            ]
        );
    }
);
