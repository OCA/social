/** @odoo-module */

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
        run: "text Test Forward",
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
        trigger: ".o_list_table td[name='complete_name']:contains('Test Forward')",
    },
];
registry.category("web_tour.tours").add("mail_forward.mail_forward_tour", {
    test: true,
    url: "/web",
    steps: () => [
        ...contact_steps,
        {
            content: "Hover a message",
            trigger: "div.o-mail-Message[aria-label='Message'] button.dropdown-toggle",
            run: "click",
        },
        {
            content: "Forward a message",
            trigger: ".mail_forward_message",
            run: "click",
        },
        {
            content: "Select a Forward",
            trigger: ".o_field_widget[name=partner_ids] input",
            extra_trigger: ".modal-dialog",
            run: "text Forward",
        },
        {
            content: "Valid Forward",
            trigger: ".ui-menu-item a:contains(Forward)",
            run: "click",
            in_modal: false,
        },
        {
            content: "Send mail",
            trigger: "button[name=action_send_mail]",
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
