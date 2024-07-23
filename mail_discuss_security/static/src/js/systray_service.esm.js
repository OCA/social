/** @odoo-module **/

import {MessagingMenuContainer} from "@mail/components/messaging_menu_container/messaging_menu_container";
import {registry} from "@web/core/registry";
import session from "web.session";

const systrayRegistry = registry.category("systray");

export const systrayService = {
    start() {
        session
            .user_has_group("mail_discuss_security.group_discuss")
            .then(function (has_group) {
                if (!has_group) {
                    systrayRegistry.remove("mail.MessagingMenuContainer", {
                        Component: MessagingMenuContainer,
                    });
                }
            });
    },
};

const serviceRegistry = registry.category("services");
serviceRegistry.add("mail_discuss_security_systray_service", systrayService);
