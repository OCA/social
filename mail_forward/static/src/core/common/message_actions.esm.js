/* @odoo-module */
/*  Copyright 2024 Tecnativa - Carlos Lopez
    License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
*/

import {_t} from "@web/core/l10n/translation";
import {ForwardMessage} from "../../components/forward_message/forward_message.esm";
import {messageActionsRegistry} from "@mail/core/common/message_actions";

messageActionsRegistry.add("forward", {
    callComponent: ForwardMessage,
    props: (component) => ({message: component.props.message}),
    condition: (component) =>
        component.props.message.is_discussion && !component.props.message.is_note,
    sequence: 75,
    title: _t("Forward"),
});
