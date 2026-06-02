/** @odoo-module **/

import tour from "web_tour.tour";

tour.register(
    "mail_edit_move_message_tour",
    {
        test: true,
    },
    [
        {
            trigger: ".o_web_client",
            content: "Wait for the web client.",
        },
        {
            trigger: ".o_action_manager",
            content: "Wait for the action manager.",
        },
        {
            trigger: ".o_Message",
            content: "Hover the chatter message.",
            run: function (actions) {
                actions.auto(".o_Message");
            },
        },
        {
            trigger: ".o_MessageActionView_actionMove",
            content: "Click the move message button.",
        },
        {
            trigger: ".o_notification",
            content: "Move helper notification is shown.",
        },
        {
            trigger: ".modal-dialog",
            content: "Mail edit wizard is opened.",
        },
    ]
);
