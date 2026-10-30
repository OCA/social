/** @odoo-module */
/*  Copyright 2024 Tecnativa - Carlos Lopez
    License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
*/
import {registry} from "@web/core/registry";
const contact_steps = [
    {
        trigger: ".o_navbar_apps_menu button",
    },
    {
        trigger: '.o_app[data-menu-xmlid="contacts.menu_contacts"]',
    },
    {
        content: "Search Contact",
        trigger: ".o_searchview_input",
        run: "text Test",
    },
    {
        trigger: ".o_menu_item",
        content: "Validate search",
        run: "click",
    },
    {
        content: "Switch to list view",
        trigger: ".o_list",
        run: "click",
    },
    {
        content: "Open contact",
        trigger: ".o_list_table td[name='complete_name']:contains('Test')",
    },
];
registry.category("web_tour.tours").add("mail_print.mail_print_tour", {
    test: true,
    url: "/web",
    steps: () => [
        ...contact_steps,
        {
            content: "Hover a message",
            trigger: "div.o-mail-Message[aria-label='Message']",
            run: "click",
        },
        {
            content: "Print a message",
            trigger: ".mail_print_message",
            run: "click",
        },
    ],
});

registry.category("web_tour.tours").add("mail_print.mail_note_not_print_tour", {
    test: true,
    url: "/web",
    steps: () => [
        ...contact_steps,
        {
            content: "Hover a note",
            trigger: "div.o-mail-Message[aria-label='Note']",
            run: "click",
        },
        {
            content: "Verify that the Print button does not exist.",
            trigger: "div.o-mail-Message[aria-label='Note']:not(.mail_print_message)",
        },
    ],
});
