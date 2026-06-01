import {_t} from "@web/core/l10n/translation";
import {threadActionsRegistry} from "@mail/core/common/thread_actions";

threadActionsRegistry
    .add("open-gw-new-partner", {
        condition({owner, thread}) {
            if (
                thread?.model !== "discuss.channel" ||
                (owner.props.chatWindow && !owner.props.chatWindow.isOpen)
            ) {
                return false;
            }
            if (thread._guestChecked) {
                return Boolean(thread._cachedGuestId);
            }
            const orm = owner.env.services.orm;
            (async () => {
                const members = await orm.silent.searchRead(
                    "discuss.channel.member",
                    [["channel_id", "=", thread.id]],
                    ["guest_id"]
                );
                const guestMembers = members.filter((m) => m.guest_id);
                if (guestMembers.length === 1) {
                    thread._cachedGuestId = guestMembers[0].guest_id;
                } else {
                    thread._cachedGuestId = null;
                }
                thread._guestChecked = true;
                owner.render?.();
            })();
            return false;
        },
        icon: "fa fa-fw fa-address-book",
        name: _t("New Partner"),
        async open({owner, thread}) {
            const guestId = thread._cachedGuestId;
            if (!guestId) return;
            await owner.env.services.action.doAction({
                type: "ir.actions.act_window",
                res_model: "mail.guest.manage",
                context: {default_guest_id: guestId[0]},
                views: [[false, "form"]],
                target: "new",
            });
        },
        iconLarge: "fa fa-fw fa-lg fa-address-book",
        sequence: 18,
    })
    .add("open-gw-profile", {
        condition({owner, thread}) {
            if (
                thread?.model !== "discuss.channel" ||
                (owner.props.chatWindow && !owner.props.chatWindow.isOpen)
            ) {
                return false;
            }
            if (thread._partnerIdChecked) {
                return Boolean(thread._cachedPartnerId);
            }
            const orm = owner.env.services.orm;
            (async () => {
                const channelData = await orm.silent.searchRead(
                    "discuss.channel",
                    [["id", "=", thread.id]],
                    ["gateway_channel_token"]
                );
                if (channelData[0]?.gateway_channel_token) {
                    const gatewayChannel = await orm.silent.searchRead(
                        "res.partner.gateway.channel",
                        [["gateway_token", "=", channelData[0].gateway_channel_token]],
                        ["partner_id"]
                    );
                    thread._cachedPartnerId = Array.isArray(
                        gatewayChannel[0]?.partner_id
                    )
                        ? gatewayChannel[0].partner_id[0]
                        : gatewayChannel[0]?.partner_id;
                } else {
                    thread._cachedPartnerId = thread.correspondent?.persona?.id;
                }
                thread._partnerIdChecked = true;
                owner.render?.();
            })();
            return false;
        },
        icon: "fa fa-fw fa-user-circle-o",
        name: _t("Open Contact"),
        async open({owner, thread}) {
            const partnerId = thread._cachedPartnerId;
            await owner.env.services.action.doAction({
                type: "ir.actions.act_window",
                res_model: "res.partner",
                res_id: partnerId,
                views: [[false, "form"]],
            });
        },
        iconLarge: "fa fa-fw fa-lg fa-user-circle-o",
        sequence: 17,
    });
