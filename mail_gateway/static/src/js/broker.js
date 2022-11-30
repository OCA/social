odoo.define("mail_broker/static/src/broker.js", function (require) {
    "use strict";
    const components = {
        Discuss: require("mail_broker/static/src/discuss.js"),
    };
    const AbstractAction = require("web.AbstractAction");
    const {action_registry} = require("web.core");

    const {Component} = owl;

    var Broker = AbstractAction.extend({
        template: "mail.widgets.Discuss",
        hasControlPanel: false,
        loadControlPanel: false,
        withSearchBar: false,
        searchMenuTypes: ["filter", "favorite"],
        /**
         * @override {web.AbstractAction}
         * @param {web.ActionManager} parent
         * @param {Object} action
         * @param {Object} [action.context]
         * @param {String} [action.context.active_id]
         * @param {Object} [action.params]
         * @param {String} [action.params.default_active_id]
         * @param {Object} [options={}]
         */
        init(parent, action, options = {}) {
            this._super(...arguments);
            // Control panel attributes
            this.action = action;
            this.actionManager = parent;
            this.searchModelConfig.modelName = "mail.message";
            this.discuss = undefined;
            this.options = options;

            this.component = undefined;

            this._lastPushStateActiveThread = null;
        },
        /**
         * @override
         */
        async willStart() {
            await this._super(...arguments);
            this.env = Component.env;
            await this.env.messagingCreatedPromise;
            const initActiveId =
                this.options.active_id ||
                (this.action.context && this.action.context.active_id) ||
                (this.action.params && this.action.params.default_active_id) ||
                "mail.box_inbox";
            this.discuss = this.env.messaging.discuss;
            this.discuss.update({initActiveId});
        },
        /**
         * @override {web.AbstractAction}
         */
        destroy() {
            if (this.component) {
                this.component.destroy();
                this.component = undefined;
            }
            this._super(...arguments);
        },
        /**
         * @override {web.AbstractAction}
         */
        on_attach_callback() {
            this._super(...arguments);
            if (this.component) {
                // Prevent twice call to on_attach_callback (FIXME)
                return;
            }
            const DiscussComponent = components.Discuss;
            this.component = new DiscussComponent();
            this._pushStateActionManagerEventListener = (ev) => {
                ev.stopPropagation();
                if (this._lastPushStateActiveThread === this.discuss.thread) {
                    return;
                }
                this._pushStateActionManager();
                this._lastPushStateActiveThread = this.discuss.thread;
            };

            this.el.addEventListener(
                "o-push-state-action-manager",
                this._pushStateActionManagerEventListener
            );
            return this.component.mount(this.el);
        },
        /**
         * @override {web.AbstractAction}
         */
        on_detach_callback() {
            this._super(...arguments);
            if (this.component) {
                this.component.destroy();
            }
            this.component = undefined;
            this.el.removeEventListener(
                "o-push-state-action-manager",
                this._pushStateActionManagerEventListener
            );
            this._lastPushStateActiveThread = null;
        },

        // --------------------------------------------------------------------------
        // Private
        // --------------------------------------------------------------------------

        /**
         * @private
         */
        _pushStateActionManager() {
            this.actionManager.do_push_state({
                action: this.action.id,
                active_id: this.discuss.activeId,
            });
        },
    });
    action_registry.add("mail.broker", Broker);

    return Broker;
});
