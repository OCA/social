odoo.define("mail_broker/static/src/discuss.js", function (require) {
    "use strict";

    const Discuss = require("mail/static/src/components/discuss/discuss.js");
    const DiscussSidebar = require("mail/static/src/components/discuss_sidebar/discuss_sidebar.js");
    const DiscussSidebarItem = require("mail/static/src/components/discuss_sidebar_item/discuss_sidebar_item.js");

    const {Component} = owl;

    class BrokerDiscussSidebarItem extends DiscussSidebarItem {
        get counter() {
            if (this.thread.channel_type === "broker") {
                return this.thread.broker_unread_counter;
            }
            return super.counter;
        }
    }

    class DiscussSidebarBroker extends Component {
        constructor(...args) {
            super(...args);
            this.mailBroker = this.env.models["mail.broker"].get(this.props.brokerId);
        }
        get quickSearchOrderedAndPinnedBrokerChannels() {
            return this.env.models["mail.thread"]
                .all((channel) => channel.broker_id === this.mailBroker.id)
                .sort((c1, c2) => {
                    if (!c1.lastMessage && !c2.lastMessage) {
                        return c1.id < c2.id;
                    } else if (!c2.lastMessage) {
                        return -1;
                    } else if (!c1.lastMessage) {
                        return 1;
                    }
                    return c1.lastMessage.id < c2.lastMessage.id ? -1 : 1;
                });
        }
    }
    Object.assign(DiscussSidebarBroker, {
        components: Object.assign(DiscussSidebar.components, {
            DiscussSidebarItem: BrokerDiscussSidebarItem,
        }),
        props: {
            brokerId: String,
        },
        template: "mail_broker.DiscussSidebarBroker",
    });

    class BrokerDiscussSidebar extends DiscussSidebar {
        get mailBrokers() {
            return this.env.models["mail.broker"].all();
        }
    }
    Object.assign(BrokerDiscussSidebar, {
        components: Object.assign(DiscussSidebar.components, {DiscussSidebarBroker}),
        props: DiscussSidebar.props,
        template: "mail_broker.DiscussSidebar",
    });

    class NewDiscuss extends Discuss {}
    Object.assign(NewDiscuss, {
        components: Object.assign({}, Discuss.components, {
            DiscussSidebar: BrokerDiscussSidebar,
        }),
        props: Discuss.props,
        template: Discuss.template,
    });
    return NewDiscuss;
});
