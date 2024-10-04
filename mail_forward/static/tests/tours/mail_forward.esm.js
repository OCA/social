/** @odoo-module */

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
    "mail_forward.mail_forward_tour",
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
            content: "Forward a message",
            trigger: ".o_MessageActionList_actionForward",
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
                ".o_Message_prettyBody:contains(---------- Forwarded message ---------)",
        },
    ]
);

tour.register(
    "mail_forward.mail_note_not_forward_tour",
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
            content: "Verify that the Forward button does not exist.",
            trigger:
                "div.o_Message.o-not-discussion:not(.o_MessageActionList_actionForward)",
        },
    ]
);
