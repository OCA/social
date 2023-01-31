/** @odoo-module **/

import {registerPatch} from "@mail/model/model_core";

registerPatch({
    name: "MessagingInitializer",
    recordMethods: {
        async _init({
            channels,
            companyName,
            current_partner,
            currentGuest,
            current_user_id,
            current_user_settings,
            hasLinkPreviewFeature,
            internalUserGroupId,
            menu_id,
            needaction_inbox_counter = 0,
            partner_root,
            shortcodes = [],
            starred_counter = 0,
            failedmsg_counter = 0,
        }) {
            const discuss = this.messaging.discuss;
            // Partners first because the rest of the code relies on them
            this._initPartners({
                currentGuest,
                current_partner,
                current_user_id,
                partner_root,
            });
            // Mailboxes after partners and before other initializers that might
            // manipulate threads or messages
            this._initMailboxes({
                needaction_inbox_counter,
                starred_counter,
                failedmsg_counter,
            });
            // Init mail user settings
            if (current_user_settings) {
                this.messaging.models["res.users.settings"].insert(
                    current_user_settings
                );
            }
            // Various suggestions in no particular order
            this._initCannedResponses(shortcodes);
            // FIXME: guests should have (at least some) commands available
            if (!this.messaging.isCurrentUserGuest) {
                this._initCommands();
            }
            // Channels when the rest of messaging is ready
            if (channels) {
                await this._initChannels(channels);
            }
            if (!this.exists()) {
                return;
            }
            discuss.update({menu_id});
            // Company related data
            this.messaging.update({
                companyName,
                hasLinkPreviewFeature,
                internalUserGroupId,
            });
        },

        _initMailboxes({needaction_inbox_counter, starred_counter, failedmsg_counter}) {
            this.messaging.inbox.update({counter: needaction_inbox_counter});
            this.messaging.starred.update({counter: starred_counter});
            this.messaging.failedmsg.update({counter: failedmsg_counter});
        },
    },
});
