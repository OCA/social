/** @odoo-module **/

import {Message} from "@mail/components/message/message";
import {registerMessagingComponent} from "@mail/utils/messaging_component";

export class FailedMessage extends Message {}

FailedMessage.props = {record: Object, isFailedMessage: true};
FailedMessage.template = "mail_tracking.FailedMessage";

registerMessagingComponent(FailedMessage);
