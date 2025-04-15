/* Copyright 2016 Jairo Llopis <jairo.llopis@tecnativa.com>
 * License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl). */
import {registry} from "@web/core/registry";

registry
    .category("web_tour.tours")
    .add("mass_mailing_custom_unsubscribe_tour_contact", {
        test: true,
        steps: () => [
            {
                content: "Confirm unsubscribe",
                trigger: "button:contains('Unsubscribe')",
                run: "click",
            },
            {
                content: "Confirm unsubscribe",
                trigger: "p:contains('Successfully unsubscribed!')",
            },
            {
                content: "Confirm unsubscribe",
                trigger: "a:contains('Manage Subscriptions')",
                run: "click",
            },
            {
                content: "Choose 'Other' reason",
                trigger: "fieldset label:contains('Other')",
                run: "click",
            },
            {
                content: "Write feedback reason",
                trigger: "textarea[name='feedback']",
                run: "edit My feedback",
            },
            {
                content: "Send reason",
                trigger: "button#button_feedback",
                run: "click",
            },
            {
                content: "Confirmation feedback is sent",
                trigger:
                    "div#o_mailing_subscription_feedback_info span:contains('Sent. Thanks you for your feedback!')",
            },
        ],
    });
