/** @odoo-module **/

import {registerMessagingComponent} from "@mail/utils/messaging_component";
import {useComponentToModel} from "@mail/component_hooks/use_component_to_model";

const {Component} = owl;

class GatewayFollowerView extends Component {
    /**
     * @override
     */
    setup() {
        super.setup();
        useComponentToModel({fieldName: "component"});
    }
    get composerGatewayFollower() {
        return this.props.record;
    }
    onChangeGatewayChannel(ev) {
        this.props.record.update({
            channel: parseInt(ev.target.options[ev.target.selectedIndex].value, 10),
        });
    }
}

Object.assign(GatewayFollowerView, {
    props: {record: Object},
    template: "mail_gateway.GatewayFollowerView",
});

registerMessagingComponent(GatewayFollowerView);
