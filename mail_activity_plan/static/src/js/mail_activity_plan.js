odoo.define("mail_activity_plan.mail_activity_plan", function (require) {
    "use strict";

    const ListController = require("web.ListController");
    const FormController = require("web.FormController");
    var core = require("web.core");
    var _t = core._t;

    ListController.include({
        async _actionWizardMailActivityPlan() {
            const state = this.model.get(this.handle);
            const resIds = await this.getSelectedIdsWithDomain();
            this.do_action("mail_activity_plan.action_wizard_mail_activity_plan", {
                additional_context: {
                    default_res_model: state.model,
                    active_ids: resIds,
                },
                on_close: () => {
                    this.update({}, {reload: false});
                },
            });
        },
        willStart: function () {
            var getMailActivityPlans = this._rpc({
                model: "mail.activity.plan",
                method: "get_total_plans_from_model",
                args: [this.modelName],
            }).then((total) => {
                this.total_mail_activity_plan = total;
            });
            return Promise.all([
                this._super.apply(this, arguments),
                getMailActivityPlans,
            ]);
        },
        _getActionMenuItems: function () {
            var menuItems = this._super.apply(this, arguments);
            if (menuItems && this.total_mail_activity_plan > 0) {
                menuItems.items.other.push({
                    description: _t("Launch Activity Plan"),
                    callback: () => this._actionWizardMailActivityPlan(),
                });
            }
            return menuItems;
        },
    });
    FormController.include({
        async _actionWizardMailActivityPlan() {
            this.do_action("mail_activity_plan.action_wizard_mail_activity_plan", {
                additional_context: {
                    default_res_model: this.modelName,
                    active_ids: this.model.localIdsToResIds([this.handle]),
                },
                on_close: () => {
                    this.update({}, {reload: false});
                },
            });
        },
        willStart: function () {
            var getMailActivityPlans = this._rpc({
                model: "mail.activity.plan",
                method: "get_total_plans_from_model",
                args: [this.modelName],
            }).then((total) => {
                this.total_mail_activity_plan = total;
            });
            return Promise.all([
                this._super.apply(this, arguments),
                getMailActivityPlans,
            ]);
        },
        _getActionMenuItems: function () {
            var menuItems = this._super.apply(this, arguments);
            if (menuItems && this.total_mail_activity_plan > 0) {
                menuItems.items.other.push({
                    description: _t("Launch Activity Plan"),
                    callback: () => this._actionWizardMailActivityPlan(),
                });
            }
            return menuItems;
        },
    });
});
