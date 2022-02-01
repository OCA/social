/* Copyright 2016-2017 Jairo Llopis <jairo.llopis@tecnativa.com>
 * License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl). */
odoo.define("website_mass_mailing_name.editor_and_public_tour", function (require) {
    "use strict";
    const tour = require("web_tour.tour");

    tour.register(
        "mass_mailing_name_admin",
        {
            test: true,
            url: "/mass-mailing-name",
        },
        [
            {
                content: "Subscribe Admin",
                trigger: ".js_subscribe_btn",
            },
            {
                content: "Subscription successful",
                trigger: ".btn-success.js_subscribed_btn:not('d-none')",
            },
        ]
    );

    tour.register(
        "mass_mailing_name_public",
        {
            test: true,
            url: "/mass-mailing-name",
        },
        [
            {
                content: "Remove name and email",
                extra_trigger: "div.s_newsletter_subscribe_form.js_subscribe",
                trigger: ".js_subscribe_name",
                run: function () {
                    $(".js_subscribe_name").val("");
                    $(".js_subscribe_email").val("");
                },
            },
            {
                content: "Try to subscribe without data",
                trigger: ".js_subscribe_btn",
            },
            {
                content: "Enter a name",
                extra_trigger: "div.s_newsletter_subscribe_form.js_subscribe",
                trigger: ".js_subscribe_name",
                run: "text Visitor",
            },
            {
                content: "Try to subscribe without email",
                trigger: ".js_subscribe_btn",
            },
            {
                content: "Remove the name",
                extra_trigger: "div.s_newsletter_subscribe_form.js_subscribe",
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
                extra_trigger: "div.s_newsletter_subscribe_form.js_subscribe",
                trigger: "input.js_subscribe_name",
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
                extra_trigger: "div.s_newsletter_subscribe_form.js_subscribe",
                trigger: ".js_subscribe_email",
                run: "text example@example.com",
            },
            {
                content: "Try to subscribe with good information",
                trigger: ".js_subscribe_btn",
            },
            {
                content: "Subscription successful",
                trigger: ".btn-success.js_subscribed_btn:not('d-none')",
            },
        ]
    );
});
