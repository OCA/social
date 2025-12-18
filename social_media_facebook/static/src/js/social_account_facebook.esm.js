import {SocialAccount} from "@social_media_base/components/social_account/social_account.esm";
import {patch} from "@web/core/utils/patch";
import {useService} from "@web/core/utils/hooks";

// Patch the SocialAccount component to add account form navigation
patch(SocialAccount.prototype, {
    setup() {
        super.setup();
        this.action = useService("action");
    },

    /**
     * Handle card click to open account form
     *
     * @param {Object} account - The social.account record data
     */
    async onCardClick(account) {
        // Open the account form view
        await this.action.doAction({
            name: account.name || "Social Account",
            type: "ir.actions.act_window",
            res_model: "social.account",
            res_id: account.id,
            views: [[false, "form"]],
            target: "current",
        });
    },
});
