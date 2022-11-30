odoo.define("mail_broker/static/src/js/broker_model.js", function (require) {
    "use strict";

    const {
        registerNewModel,
        registerInstancePatchModel,
        registerFieldPatchModel,
        registerClassPatchModel,
    } = require("mail/static/src/model/model_core.js");
    const {attr, many2one} = require("mail/static/src/model/model_field.js");

    function factoryBroker(dependencies) {
        class Broker extends dependencies["mail.model"] {}
        Broker.modelName = "mail.broker";
        Broker.fields = {
            id: attr(),
            name: attr(),
        };

        return Broker;
    }
    registerNewModel("mail.broker", factoryBroker);
    registerInstancePatchModel(
        "mail.messaging_initializer",
        "mail_broker/static/src/js/broker_model.js",
        {
            async _init({broker_slots}) {
                _.each(broker_slots, (broker_slot) =>
                    this.env.models["mail.broker"].insert(
                        Object.assign({model: "mail.broker"}, broker_slot)
                    )
                );
                return this._super(...arguments);
            },
        }
    );
    registerInstancePatchModel(
        "mail.discuss",
        "mail_broker/static/src/js/broker_model.js",
        {
            async openBrokerChannel(thread) {
                this.update({
                    brokerChannel: [["link", thread]],
                });
                this.focus();
                this.env.bus.trigger("do-action", {
                    action: "mail_broker.mail_broker_action_window",
                    options: {
                        active_id: this.threadToActiveId(this),
                        clear_breadcrumbs: false,
                        on_reverse_breadcrumb: () => this.close(),
                    },
                });
            },
        }
    );
    registerClassPatchModel(
        "mail.thread",
        "mail_broker/static/src/js/broker_model.js",
        {
            convertData(data) {
                const data2 = this._super(data);
                data2.broker_id = data.broker_id;
                data2.broker_unread_counter = data.broker_unread_counter;
                return data2;
            },
        }
    );

    registerFieldPatchModel(
        "mail.discuss",
        "mail_broker/static/src/js/broker_model.js",
        {
            brokerChannel: many2one("mail.thread"),
        }
    );
    registerFieldPatchModel(
        "mail.thread",
        "mail_broker/static/src/js/broker_model.js",
        {
            broker_id: attr(),
            broker_unread_counter: attr(),
        }
    );
});
