odoo.define("mail_edit.tour", function (require) {
    "use strict";

    var core = require("web.core");
    var tour = require("web_tour.tour");

    var _t = core._t;

    tour.register(
        "mail_edit_tour",
        {.o_DiscussSidebar_item:contains("general")
            url: "/web",
        },
        [
            // 1. open Apps menu
            tour.stepUtils.showAppsMenuItem(),
            // 2. Open Discuss menu
            {
                trigger: '.o_app[data-menu-xmlid="mail.menu_root_discuss"]',
                content: _t("Open Apps -> Discuss menu"),
                position: "right",
                edition: "community",
            },
            // 3. Open "general" channel
            {
                trigger: '.o_DiscussSidebar_item:contains("general")',
                run: 'click',
            },
            // 4. As superuser, other user's messages should also be editable
            {
                trigger: '.o_Message:not(:contains("Marc Demo")) .o_Message_headerCommands:has(".o_Message_Edit"):first',
                run: 'click',
                content: _t("Click the Edit Icon on the first message"),
                position: "bottom",
            },
            // 5. Try to edit a message and save
            {
                trigger: "input[name=subject]",
                content: _t("Edit Mail Subject"),
                run: "text New Subject",
            },
            {
                trigger: "button span:contains(Save)",
                extra_trigger: ".modal-footer",
                content: _t("Save Changes"),
                run: "click",
            },
            // 6. Try to delete a message
            {
                trigger: ".o_Message_Delete:first",
                content: _t("Click the Delete Icon on the first message"),
                position: "bottom",
            },
            {
                trigger: "button span:contains(Ok)",
                extra_trigger: ".modal-footer",
                content: _t("Confirm Deletion"),
                run: "click",
            },
        ]
    );

    tour.register(
        "mail_edit_tour_no_superuser",
        {
            url: "/web",
        },
        [
            // 1. open Apps menu
            tour.stepUtils.showAppsMenuItem(),
            // 2. Open Discuss menu
            {
                trigger: '.o_app[data-menu-xmlid="mail.menu_root_discuss"]',
                content: _t("Open Apps -> Discuss menu"),
                position: "right",
                edition: "community",
            },
            // 3. Open "general" channel
            {
                trigger: '.o_DiscussSidebar_item:contains("general")',
                run: 'click',
            },
            // 4. Other user's messages should not be editable
            {
                trigger: '.o_Message:not(:contains("Marc Demo")) .o_Message_headerCommands:not(:has(".o_Message_Edit"))',
                run: function() {},  // just a check
            },
            // 4. Own messages should be editable
            {
                trigger: '.o_Message:not(:contains("Marc Demo")) .o_Message_headerCommands:has(".o_Message_Edit"):first',
                run: 'click',
                content: _t("Click the Edit Icon on the first message"),
                position: "bottom",
            },
            {
                trigger: "input[name=subject]",
                content: _t("Edit Mail Subject"),
                run: "text New Subject",
            },
            {
                trigger: "button span:contains(Save)",
                extra_trigger: ".modal-footer",
                content: _t("Save Changes"),
                run: "click",
            },
            {
                trigger: ".o_Message_Delete:first",
                content: _t("Click the Delete Icon on the first message"),
                position: "bottom",
            },
            {
                trigger: "button span:contains(Ok)",
                extra_trigger: ".modal-footer",
                content: _t("Confirm Deletion"),
                run: "click",
            },
        ]
    );
});
