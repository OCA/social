odoo.define("mail_tracking/static/src/js/discuss/discuss.js", function (require) {
    "use strict";

    const {attr} = require("mail/static/src/model/model_field.js");
    const {
        registerInstancePatchModel,
        registerFieldPatchModel,
        registerClassPatchModel,
    } = require("mail/static/src/model/model_core.js");
    const {one2one, many2one} = require("mail/static/src/model/model_field.js");

    registerInstancePatchModel(
        "mail.messaging_initializer",
        "mail/static/src/models/messaging_initializer/messaging_initializer.js",
        {
            async start() {
                this.messaging.update({
                    failedmsg: [
                        [
                            "create",
                            {
                                id: "failedmsg",
                                isServerPinned: true,
                                model: "mail.box",
                                name: this.env._t("Failed"),
                            },
                        ],
                    ],
                });
                return this._super(...arguments);
            },
            async _init({
                channel_slots,
                commands = [],
                current_partner,
                current_user_id,
                mail_failures = {},
                mention_partner_suggestions = [],
                menu_id,
                moderation_channel_ids = [],
                moderation_counter = 0,
                needaction_inbox_counter = 0,
                partner_root,
                public_partner,
                public_partners,
                shortcodes = [],
                starred_counter = 0,
                failed_counter = 0,
            }) {
                const discuss = this.messaging.discuss;
                // Partners first because the rest of the code relies on them
                this._initPartners({
                    current_partner,
                    current_user_id,
                    moderation_channel_ids,
                    partner_root,
                    public_partner,
                    public_partners,
                });
                // Mailboxes after partners and before other initializers that might
                // manipulate threads or messages
                this._initMailboxes({
                    moderation_channel_ids,
                    moderation_counter,
                    needaction_inbox_counter,
                    starred_counter,
                    failed_counter,
                });
                // Various suggestions in no particular order
                this._initCannedResponses(shortcodes);
                this._initCommands(commands);
                this._initMentionPartnerSuggestions(mention_partner_suggestions);
                // Channels when the rest of messaging is ready
                await this.async(() => this._initChannels(channel_slots));
                // Failures after channels
                this._initMailFailures(mail_failures);
                discuss.update({menu_id});
            },

            _initMailboxes({
                moderation_channel_ids,
                moderation_counter,
                needaction_inbox_counter,
                starred_counter,
                failed_counter,
            }) {
                this.env.messaging.inbox.update({counter: needaction_inbox_counter});
                this.env.messaging.starred.update({counter: starred_counter});
                this.env.messaging.failedmsg.update({counter: failed_counter});
                if (moderation_channel_ids.length > 0) {
                    this.messaging.moderation.update({
                        counter: moderation_counter,
                        isServerPinned: true,
                    });
                }
            },
        }
    );

    registerFieldPatchModel(
        "mail.messaging",
        "mail/static/src/models/messaging/messaging.js",
        {
            failedmsg: one2one("mail.thread"),
        }
    );

    registerInstancePatchModel(
        "mail.thread_cache",
        "mail/static/src/models/thread_cache/thread_cache.js",
        {
            _extendMessageDomain(domain) {
                const thread = this.thread;
                if (thread === this.env.messaging.failedmsg) {
                    return domain.concat([["is_failed_message", "=", true]]);
                }
                return this._super(...arguments);
            },
        }
    );

    registerFieldPatchModel(
        "mail.message",
        "mail/static/src/models/message/message.js",
        {
            messagingFailedmsg: many2one("mail.thread", {
                related: "messaging.failedmsg",
            }),
            isFailed: attr({
                default: false,
            }),
        }
    );

    registerClassPatchModel(
        "mail.message",
        "mail/static/src/models/message/message.js",
        {
            convertData(data) {
                const data2 = this._super(data);
                if ("is_failed_message" in data) {
                    data2.isFailed = data.is_failed_message;
                }
                return data2;
            },
        }
    );
});
