/** @odoo-module **/

import { registerPatch } from '@mail/model/model_core';
import {many, attr, one} from "@mail/model/model_field";
import {insert, set} from "@mail/model/model_field_command";

registerPatch({
    name: 'MessagingInitializer',
    recordMethods: {
        async start() {
            this.messaging.update({
                failedmsg: insert({
                    id: "failedmsg",
                    isServerPinned: true,
                    model: "mail.box",
                    name: this.env._t("Failed"),
                }),
            });
            return this._super(...arguments);
        },
        async _init({
            channels,
            companyName,
            current_partner,
            currentGuest,
            current_user_id,
            current_user_settings,
            mail_failures = [],
            menu_id,
            needaction_inbox_counter = 0,
            partner_root,
            public_partners,
            shortcodes = [],
            starred_counter = 0,
            failed_counter = 0,
        }) {
            const discuss = this.messaging.discuss;
            // Partners first because the rest of the code relies on them
            this._initPartners({
                currentGuest,
                current_partner,
                current_user_id,
                partner_root,
                public_partners,
            });
            // Mailboxes after partners and before other initializers that might
            // manipulate threads or messages
            this._initMailboxes({
                needaction_inbox_counter,
                starred_counter,
                failed_counter,
            });
            // Init mail user settings
            if (current_user_settings) {
                this._initPartners(current_user_settings);
            } else {
                this.messaging.update({
                    userSetting: insert({
                        // Fake id for guest
                        id: -1,
                    }),
                });
            }
            // Various suggestions in no particular order
            this._initCannedResponses(shortcodes);
            // FIXME: guests should have (at least some) commands available
            if (!this.messaging.isCurrentUserGuest) {
                this._initCommands();
            }
            // Channels when the rest of messaging is ready
            await this._initChannels(channels);
            // Failures after channels
            this._initMailFailures(mail_failures);
            discuss.update({menu_id});
            // Company related data
            this.messaging.update({companyName});
        },

        _initMailboxes({needaction_inbox_counter, starred_counter, failed_counter}) {
            this.messaging.inbox.update({counter: needaction_inbox_counter});
            this.messaging.starred.update({counter: starred_counter});
            this.messaging.failedmsg.update({counter: failed_counter});
        },
    }
});

registerPatch({
    name: 'Messaging',
    fields: {
        failedmsg: one('Thread'),
    },
});

registerPatch({
    name: 'ThreadCache',
    recordMethods: {
        _extendMessageDomain(domain) {
            const thread = this.thread;
            if (thread === this.env.messaging.failedmsg) {
                return domain.concat([["is_failed_message", "=", true]]);
            }
            return this._super(...arguments);
        },
    }
});

registerPatch({
    name: 'Message',
    modelMethods: {
        convertData(data) {
            const res = this._super(data);
            if ("is_failed_message" in data) {
                res.isFailed = data.is_failed_message;
            }
            return res;
        },
    },
    fields: {
        messagingFailedmsg: many("Thread", {
            related: "messaging.failedmsg",
        }),
        isFailed: attr({
            default: false,
        })
    },
    recordMethods: {
        _computeThreads() {
            const threads = [];
            if (this.isHistory && this.messaging.history) {
                threads.push(this.messaging.history);
            }
            if (this.isNeedaction && this.messaging.inbox) {
                threads.push(this.messaging.inbox);
            }
            if (this.isStarred && this.messaging.starred) {
                threads.push(this.messaging.starred);
            }
            if (this.isFailed && this.messaging.failedmsg) {
                threads.push(this.messaging.failedmsg);
            }
            if (this.originThread) {
                threads.push(this.originThread);
            }
            return set(threads);
        },
    },
});

