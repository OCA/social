/** @odoo-module */
/*  Copyright 2024 Tecnativa - Carlos Lopez
    License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
*/
import tour from "web_tour.tour";
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
        trigger: ".o_list_table td[name='display_name']:contains('Test')",
    },
];
tour.register(
    "mail_print.mail_print_tour",
    {
        test: true,
        url: "/web",
    },
    [
        ...contact_steps,
        {
            content: "Open Chat",
            trigger: ".o_ChatterTopbar_buttonSendMessage",
            run: "click",
        },
        {
            content: "Write a message",
            trigger: ".o_ComposerTextInput_textarea",
            run: "text Hello World",
        },
        {
            content: "Post a message",
            trigger: ".o_Composer_buttonSend",
        },
        {
            content: "Hover a message",
            trigger: "div.o_Message.o-discussion",
            run: "click",
        },
        {
            content: "Print a message",
            trigger: ".o_MessageActionList_actionPrint",
            run: "click",
        },
    ]
);

tour.register(
    "mail_print.mail_note_not_print_tour",
    {
        test: true,
        url: "/web",
    },
    [
        ...contact_steps,
        {
            content: "Open Chat",
            trigger: ".o_ChatterTopbar_buttonLogNote",
            run: "click",
        },
        {
            content: "Write a note",
            trigger: ".o_ComposerTextInput_textarea",
            run: "text This is a note",
        },
        {
            content: "Post a note",
            trigger: ".o_Composer_buttonSend",
        },
        {
            content: "Hover a note",
            trigger: "div.o_Message.o-not-discussion",
            run: "click",
        },
        {
            content: "Verify that the Print button does not exist.",
            trigger:
                "div.o_Message.o-not-discussion:not(.o_MessageActionList_actionPrint)",
        },
    ]
);
