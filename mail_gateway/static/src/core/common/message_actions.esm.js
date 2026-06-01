import {_t} from "@web/core/l10n/translation";
import {messageActionsRegistry} from "@mail/core/common/message_actions";

messageActionsRegistry
    .add("link_gateway_to_thread", {
        condition: ({message, thread}) =>
            message.gateway_type && thread.model === "discuss.channel",
        icon: "fa fa-link",
        name: _t("Link to thread"),
        onSelected: ({owner}) => owner.onClickLinkGatewayToThread(),
        sequence: 20,
    })
    .add("send_with_gateway", {
        condition: ({message, thread}) =>
            !message.gateway_type && thread.model !== "discuss.channel",
        icon: "fa fa-share-square-o",
        name: _t("Send with gateway"),
        onSelected: ({owner}) => owner.onClickSendWithGateway(),
        sequence: 20,
    });
