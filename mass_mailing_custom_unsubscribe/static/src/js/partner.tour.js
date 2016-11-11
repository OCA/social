/* Copyright 2016 Jairo Llopis <jairo.llopis@tecnativa.com>
 * License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl). */
odoo.define("mass_mailing_custom_unsubscribe.partner_tour",
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
        id: "mass_mailing_custom_unsubscribe_tour_partner",
        name: "Mass mailing partner unsubscribes",
        mode: "test",
        steps: [
            {
                title: "Choose other reason",
                element: ".radio:contains('Other reason') " +
                         ":radio:not(:checked)",
                waitFor: "#reason_form .js_unsubscription_reason",
            },
            {
                title: "Switch to not interested reason",
                element: ".radio:contains(\"I'm not interested\") " +
                         ":radio:not(:checked)",
                waitFor: "[name='details']:propRequired",
            },
            {
                title: "Unsubscribe",
                element: "#reason_form :submit",
                waitNot: "[name='details']:propRequired",
            },
            {
                title: "Successfully unsubscribed",
                waitFor: ".alert-success:contains(" +
                         "'Your changes have been saved.')",
                waitNot: "#reason_form",
            },
        ]
    });

    return Tour.tours.mass_mailing_custom_unsubscribe_tour_partner;
});
