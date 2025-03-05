/** @odoo-module **/

import {clear} from "@mail/model/model_field_command";
import {registerPatch} from "@mail/model/model_core";

registerPatch({
    name: "DiscussSidebarCategoryItem",
    fields: {
        avatarUrl: {
            compute() {
                // We will use the avatar provied by the channel by default
                if (this.channel.channel_type === "gateway") {
                    return `/web/image/mail.channel/${this.channel.id}/avatar_128?unique=${this.channel.avatarCacheKey}`;
                }
                return this._super();
            },
        },
        categoryCounterContribution: {
            compute() {
                if (this.channel.channel_type === "gateway") {
                    return this.channel.localMessageUnreadCounter > 0 ? 1 : 0;
                }
                return this._super();
            },
        },
        counter: {
            compute() {
                if (this.channel.channel_type === "gateway") {
                    return this.channel.localMessageUnreadCounter;
                }
                return this._super();
            },
        },
        hasThreadIcon: {
            compute() {
                if (this.channel.channel_type === "gateway") {
                    return clear();
                }
                return this._super();
            },
        },
        hasUnpinCommand: {
            compute() {
                if (this.channel.channel_type === "gateway") {
                    return !this.channel.localMessageUnreadCounter;
                }
                return this._super();
            },
        },
    },
});
