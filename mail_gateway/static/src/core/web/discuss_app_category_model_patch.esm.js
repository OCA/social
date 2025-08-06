import {DiscussAppCategory} from "@mail/core/public_web/discuss_app_category_model";
import {compareDatetime} from "@mail/utils/common/misc";
import {patch} from "@web/core/utils/patch";

patch(DiscussAppCategory.prototype, {
    /**
     * @param {import("models").Thread} t1
     * @param {import("models").Thread} t2
     */
    sortThreads(t1, t2) {
        if (this.id === "gateway") {
            return (
                compareDatetime(t2.lastInterestDateTime, t1.lastInterestDateTime) ||
                t2.id - t1.id
            );
        }
        return super.sortThreads(t1, t2);
    },
});
