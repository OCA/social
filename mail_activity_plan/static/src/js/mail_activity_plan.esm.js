/** @odoo-module **/

import {FormController} from "@web/views/form/form_controller";
import {ListController} from "@web/views/list/list_controller";
import {onWillStart} from "@odoo/owl";
import {useService} from "@web/core/utils/hooks";
import {_lt} from "@web/core/l10n/translation";
import {patch} from "@web/core/utils/patch";

patch(FormController.prototype, "mail_activity_plan.FormControllerPatch", {
    async _actionWizardMailActivityPlan() {
        this.actionService.doAction(
            "mail_activity_plan.action_wizard_mail_activity_plan",
            {
                additionalContext: {
                    default_res_model: this.props.resModel,
                    active_ids: [this.props.resId],
                },
                on_close: () => {
                    this.update({}, {reload: false});
                },
            }
        );
    },
    setup() {
        this._super();
        this.actionService = useService("action");
        this.orm = useService("orm");
        onWillStart(async () => {
            await this._showWizardMailActivityPlan();
        });
    },
    async _showWizardMailActivityPlan() {
        const planCount = await this.orm.call(
            "mail.activity.plan",
            "get_total_plans_from_model",
            [this.props.resModel]
        );
        this.showWizardMailActivityPlan = planCount !== 0;
    },
    getActionMenuItems() {
        const actionMenus = this._super();
        if (actionMenus && this.showWizardMailActivityPlan) {
            actionMenus.other.push({
                description: _lt("Launch Activity Plan"),
                callback: () => this._actionWizardMailActivityPlan(),
            });
        }
        return actionMenus;
    },
});

patch(ListController.prototype, "mail_activity_plan", {
    async _actionWizardMailActivityPlan() {
        const resIds = await this.getSelectedResIds();
        this.actionService.doAction(
            "mail_activity_plan.action_wizard_mail_activity_plan",
            {
                additionalContext: {
                    default_res_model: this.props.resModel,
                    active_ids: resIds,
                },
                on_close: () => {
                    this.update({}, {reload: false});
                },
            }
        );
    },
    setup() {
        this._super();
        this.actionService = useService("action");
        this.orm = useService("orm");
        onWillStart(async () => {
            await this._showWizardMailActivityPlan();
        });
    },
    async _showWizardMailActivityPlan() {
        const planCount = await this.orm.call(
            "mail.activity.plan",
            "get_total_plans_from_model",
            [this.props.resModel]
        );
        this.showWizardMailActivityPlan = planCount !== 0;
    },
    getActionMenuItems() {
        const actionMenus = this._super();
        if (actionMenus && this.showWizardMailActivityPlan) {
            actionMenus.other.push({
                description: _lt("Launch Activity Plan"),
                callback: () => this._actionWizardMailActivityPlan(),
            });
        }
        return actionMenus;
    },
});
