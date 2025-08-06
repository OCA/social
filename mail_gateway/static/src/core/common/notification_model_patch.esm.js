import {Notification} from "@mail/core/common/notification_model";
import {patch} from "@web/core/utils/patch";

patch(Notification.prototype, {
    get icon() {
        if (this.gateway_type) {
            return `fa fa-${this.gateway_type}`;
        }
        return super.icon;
    },
    get statusIcon() {
        if (!this.gateway_type) {
            return super.statusIcon;
        }
        // It can be overriden on the gateway implementation
        switch (this.notification_status) {
            case "process":
                return "fa fa-hourglass-half";
            case "pending":
                return "fa fa-paper-plane-o";
            case "sent":
                return `fa fa-${this.gateway_type} text-success`;
            case "bounce":
                return `fa fa-${this.gateway_type} text-danger`;
            case "exception":
                return `fa fa-${this.gateway_type} text-danger`;
            case "ready":
                return "fa fa-send-o";
            case "canceled":
                return "fa fa-trash-o";
        }
        return "";
    },
});
