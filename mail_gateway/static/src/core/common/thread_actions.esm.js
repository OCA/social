/* @odoo-module */

import {threadActionsRegistry} from "@mail/core/common/thread_actions";
import {_t} from "@web/core/l10n/translation";
import {useComponent} from "@odoo/owl";
import {useService} from "@web/core/utils/hooks";

threadActionsRegistry
    .add("open-gw-new-partner", {
        condition(component) {
            return (
                component.thread?.model === "discuss.channel" &&
                (!component.props.chatWindow || component.props.chatWindow.isOpen) &&
                component.thread?.guestId
            );
        },
        icon: "fa fa-fw fa-address-book",
        name: _t("New Partner"),
        async setup() {
            const component = useComponent();
            const orm = useService("orm");
            let guestId = null;
            const guest = await orm.silent.searchRead(
                "mail.guest",
                [["name", "=", component.thread.name]],
                ["id"]
            );
            guestId = guest[0]?.id;
            if (guestId) {
                component.thread.guestId = guestId;
            }
        },
        async open(component) {
            const guestId = component.thread?.guestId;
            await component.env.services.action.doAction(
                {
                    type: "ir.actions.act_window",
                    res_model: "mail.guest.manage",
                    context: {default_guest_id: guestId},
                    views: [[false, "form"]],
                    target: "new",
                },
                {
                    onClose: async () => {
                        component.thread.guestId = null;
                    },
                }
            );
        },
        iconLarge: "fa fa-fw fa-lg fa-address-book",
        sequence: 18,
    })
    .add("open-gw-profile", {
        condition(component) {
            return (
                component.thread?.model === "discuss.channel" &&
                (!component.props.chatWindow || component.props.chatWindow.isOpen) &&
                !component.thread?.guestId
            );
        },
        icon: "fa fa-fw fa-user-circle-o",
        name: _t("Open Contact"),
        async open(component) {
            const orm = component.env.services.orm;
            const channelToken = await orm.silent.searchRead(
                "discuss.channel",
                [["id", "=", component.thread?.id]],
                ["gateway_channel_token"]
            );
            const partnerGatewayChannel = await orm.silent.searchRead(
                "res.partner.gateway.channel",
                [["gateway_token", "=", channelToken[0]?.gateway_channel_token]],
                ["partner_id"]
            );
            let partnerId = null;
            if (component.thread?.type === "gateway") {
                partnerId = partnerGatewayChannel[0]?.partner_id?.[0];
            } else {
                partnerId = component.thread.chatPartner?.id;
            }
            if (!partnerId) {
                return;
            }
            await component.env.services.action.doAction({
                type: "ir.actions.act_window",
                res_model: "res.partner",
                res_id: partnerId,
                views: [[false, "form"]],
            });
        },
        iconLarge: "fa fa-fw fa-lg fa-user-circle-o",
        sequence: 17,
    });
