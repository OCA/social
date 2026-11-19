import {Chatter} from "@mail/chatter/web_portal/chatter";
import {patch} from "@web/core/utils/patch";
import {useService} from "@web/core/utils/hooks";

patch(Chatter.prototype, {
    setup() {
        super.setup(...arguments);
        this.actionService = useService("action");
        this.ormService = useService("orm");
    },

    async onClickListActivities() {
        const thread = this.state.thread;
        if (!thread?.id) {
            return;
        }
        const action = await this.ormService.call(
            thread.model,
            "redirect_to_activities",
            [[]],
            {
                id: thread.id,
                model: thread.model,
            }
        );
        await this.actionService.doAction(action, {
            onClose: () => this.load(thread, ["activities", "messages"]),
        });
    },
});
