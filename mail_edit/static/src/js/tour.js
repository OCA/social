odoo.define("mail_edit.tour", function (require) {
    "use strict";

    var core = require("web.core");
    var tour = require("web_tour.tour");

    var _t = core._t;

    tour.register(
        "mail_edit_tour",
        {
            url: "/web",
        },
        [
            tour.stepUtils.showAppsMenuItem(),
            {
                trigger: '.o_app[data-menu-xmlid="mail.menu_root_discuss"]',
                content: _t("Open Apps -> Discuss menu"),
                position: "right",
                edition: "community",
            },
            {
                trigger:
                    '.o_DiscussSidebar_groupHeaderItemAdd[title="Add or join a channel"]',
                content: _t("Channels -> Add button"),
                position: "bottom",
            },
            {
                trigger: ".o_DiscussSidebar_itemNew",
                content: _t("Add a new Channel"),
                position: "right",
                run: function (actions) {
                    actions.text("Mail-Edit Channel", this.$anchor.find("input"));
                },
            },
            {
                trigger: ".o_Message_Edit:first",
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
