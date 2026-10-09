/** @odoo-module **/
/*
    Copyright 2022 Camptocamp SA (https://www.camptocamp.com).
    @author Iván Todorovich <ivan.todorovich@camptocamp.com>
    License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
*/

import {
    afterEach,
    beforeEach,
    createRootMessagingComponent,
    start,
} from "@mail/utils/test_utils";

const {QUnit} = window;

QUnit.module(
    "mail_activity_security",
    {
        before() {
            this.createActivityComponent = async function (activity) {
                return await createRootMessagingComponent(this, "Activity", {
                    props: {activityLocalId: activity.localId},
                    target: this.widget.el,
                });
            };
            this.createActivityComponentFromData = async function (activityData) {
                return await this.createActivityComponent(
                    this.messaging.models["mail.activity"].insert(
                        this.messaging.models["mail.activity"].convertData(activityData)
                    )
                );
            };
        },
        async beforeEach() {
            beforeEach(this);
            // Default activity data
            this.defaultActivityData = {
                can_write: true,
                icon: "fa-times",
                id: 12,
                res_id: 42,
                res_model: "res.partner",
            };
            // Start the mocked environment
            const {env, widget} = await start({data: this.data});
            this.env = env;
            this.widget = widget;
        },
        afterEach() {
            afterEach(this);
        },
    },
    function () {
        QUnit.test("activity: all premissions", async function (assert) {
            assert.expect(3);
            const component = await this.createActivityComponentFromData(
                Object.assign({}, this.defaultActivityData, {
                    user_can_mark_as_done: true,
                    user_can_edit: true,
                    user_can_cancel: true,
                })
            );
            assert.ok(
                component.el.querySelector(".o_Activity_markDoneButton"),
                "Mark as Done button"
            );
            assert.ok(
                component.el.querySelector(".o_Activity_editButton"),
                "Edit button"
            );
            assert.ok(
                component.el.querySelector(".o_Activity_cancelButton"),
                "Cancel button"
            );
        });

        QUnit.test("activity: can't mark as done", async function (assert) {
            assert.expect(3);
            const component = await this.createActivityComponentFromData(
                Object.assign({}, this.defaultActivityData, {
                    user_can_mark_as_done: false,
                    user_can_edit: true,
                    user_can_cancel: true,
                })
            );
            assert.notOk(
                component.el.querySelector(".o_Activity_markDoneButton"),
                "Mark as Done button"
            );
            assert.ok(
                component.el.querySelector(".o_Activity_editButton"),
                "Edit button"
            );
            assert.ok(
                component.el.querySelector(".o_Activity_cancelButton"),
                "Cancel button"
            );
        });

        QUnit.test("activity: can't edit", async function (assert) {
            assert.expect(3);
            const component = await this.createActivityComponentFromData(
                Object.assign({}, this.defaultActivityData, {
                    user_can_mark_as_done: true,
                    user_can_edit: false,
                    user_can_cancel: true,
                })
            );
            assert.ok(
                component.el.querySelector(".o_Activity_markDoneButton"),
                "Mark as Done button"
            );
            assert.notOk(
                component.el.querySelector(".o_Activity_editButton"),
                "Edit button"
            );
            assert.ok(
                component.el.querySelector(".o_Activity_cancelButton"),
                "Cancel button"
            );
        });

        QUnit.test("activity: can't cancel", async function (assert) {
            assert.expect(3);
            const component = await this.createActivityComponentFromData(
                Object.assign({}, this.defaultActivityData, {
                    user_can_mark_as_done: true,
                    user_can_edit: true,
                    user_can_cancel: false,
                })
            );
            assert.ok(
                component.el.querySelector(".o_Activity_markDoneButton"),
                "Mark as Done button"
            );
            assert.ok(
                component.el.querySelector(".o_Activity_editButton"),
                "Edit button"
            );
            assert.notOk(
                component.el.querySelector(".o_Activity_cancelButton"),
                "Cancel button"
            );
        });
    }
);
