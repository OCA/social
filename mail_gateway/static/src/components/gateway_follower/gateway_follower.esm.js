import {Component} from "@odoo/owl";

export class GatewayFollower extends Component {
    static template = "mail_gateway.GatewayFollowerView";
    static props = ["follower", "composer"];
    setup() {
        this.channel = false;
        this.follower_channel_ids = this.props.follower.gateway_channels.map(
            (channel) => channel.id
        );
        this._clearGatewayNotifications();
    }
    get composerGatewayFollower() {
        return this.props.follower;
    }
    _getMessageData() {
        return {
            partner_id: this.props.follower.id,
            channel_type: "gateway",
            gateway_channel_id: this.channel,
        };
    }
    _clearGatewayNotifications() {
        this.props.composer.thread.gateway_notifications =
            this.props.composer.thread.gateway_notifications.filter(
                (gateway_notification) => {
                    return !this.follower_channel_ids.includes(
                        gateway_notification.gateway_channel_id
                    );
                }
            );
    }
    onChangeGatewayChannel(ev) {
        this.channel = parseInt(ev.target.options[ev.target.selectedIndex].value, 10);
        if (this.channel) {
            this.props.composer.thread.gateway_notifications.push(
                this._getMessageData()
            );
        } else {
            this._clearGatewayNotifications();
        }
    }
}
