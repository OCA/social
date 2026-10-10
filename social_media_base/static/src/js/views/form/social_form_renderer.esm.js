import {FormRenderer} from "@web/views/form/form_renderer";
import {SocialMediaMixin} from "../../app/social_media_mixin.esm";
import {useService} from "@web/core/utils/hooks";

export class SocialFormRenderer extends SocialMediaMixin(FormRenderer) {
    setup() {
        super.setup();
        this.notificationService = useService("notification");
        this.busService = this.env.services.bus_service;
        this.notif_view = "form";
        this.enableSocialNotifications();
    }
}
