import {Store} from "@mail/core/common/store_service";
import {patch} from "@web/core/utils/patch";

patch(Store.prototype, {
    async fetchData(thread, ...args) {
        const result = await super.fetchData(thread, ...args);
        thread.gateway_followers = result.gateway_followers;
        return result;
    },
    async getMessagePostParams(params) {
        const post_params = await super.getMessagePostParams(...arguments);
        if (params.thread.gateway_notifications) {
            post_params.post_data.gateway_notifications =
                params.thread.gateway_notifications;
        }
        return post_params;
    },
});
