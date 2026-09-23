/** @odoo-module */

import {registry} from "@web/core/registry";

const contact_steps = [
    {
        content: "Open apps menu",
        trigger: ".o_navbar_apps_menu button",
        run: "click",
    },
    {
        trigger: '.o_app[data-menu-xmlid="contacts.menu_contacts"]',
        run: "click",
    },
    {
        content: "Search Contact",
        trigger: ".o_searchview_input",
        run: "edit Test Forward",
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
        trigger:
            ".o_list_table .o_data_cell[name='display_name']:contains('Test Forward')",
        run: "click",
    },
];
registry.category("web_tour.tours").add("mail_forward.mail_forward_tour", {
    test: true,
    url: "/web",
    steps: () => [
        ...contact_steps,
        {
            content: "Hover a message",
            trigger: "div.o-mail-Message[aria-label='Message']",
            run: "hover",
        },
        {
            content: "Open message actions",
            trigger: "div.o-mail-Message[aria-label='Message'] button[title='Expand']",
            run: "click",
        },
        {
            content: "Forward a message",
            trigger: ".o-mail-Message-moreMenu .mail_forward_message",
            run: "click",
        },
        {
            content: "Select a Forward",
            trigger: ".modal-dialog .o_field_widget[name=partner_ids] input",
            run: "edit Forward",
        },
        {
            content: "Valid Forward",
            trigger: ".modal-dialog .ui-menu-item a:contains(Forward)",
            run: "click",
        },
        {
            content: "Send mail",
            trigger: ".modal .btn.o_mail_send",
            run: "click",
        },
        {
            content: "Check Mail Forward",
            trigger:
                "div.o-mail-Message[aria-label='Message']:contains(---------- Forwarded message ---------)",
        },
    ],
});

registry.category("web_tour.tours").add("mail_forward.mail_note_not_forward_tour", {
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
            content: "Verify that the Forward button does not exist.",
            trigger: "div.o-mail-Message[aria-label='Note']:not(.mail_forward_message)",
        },
    ],
});
