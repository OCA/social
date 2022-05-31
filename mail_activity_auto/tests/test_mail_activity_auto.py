from odoo import Command, fields
from odoo.tests.common import TransactionCase


class TestMailActivityAutoMethods(TransactionCase):
    def setUp(self):
        super(TestMailActivityAutoMethods, self).setUp()

        ActivityType = self.env["mail.activity.type"]
        IrActionsServer = self.env["ir.actions.server"]
        self.QueueJob = self.env["queue.job"]

        self.partner_model = self.env.ref("base.model_res_partner")

        self.server_action = IrActionsServer.create(
            {
                "name": "Force Archived Contacts",
                "state": "object_write",
                "model_id": self.partner_model.id,
                "fields_lines": [
                    Command.create(
                        {
                            "col1": self.env.ref("base.field_res_partner__active").id,
                            "evaluation_type": "equation",
                            "value": "False",
                        }
                    )
                ],
            }
        )

        self.activity_type_auto = ActivityType.create(
            {
                "name": "Initial Contact",
                "delay_count": 5,
                "delay_unit": "days",
                "summary": "ACT 1 : Presentation, barbecue, ... ",
                "res_model": self.partner_model.model,
                "auto": True,
                "auto_action_ids": [
                    Command.create(
                        {
                            "filter_domain": "[('is_company', '=', True)]",
                            "auto_action_id": self.server_action.id,
                        }
                    ),
                ],
            }
        )

        self.activity_type_no_auto_action = ActivityType.create(
            {
                "name": "Initial Contact",
                "delay_count": 5,
                "delay_unit": "days",
                "summary": "ACT 1 : Presentation, barbecue, ... ",
                "res_model": self.partner_model.model,
                "auto": False,
                "auto_action_ids": [
                    Command.create(
                        {
                            "filter_domain": "[('is_company', '=', True)]",
                            "auto_action_id": self.server_action.id,
                        }
                    ),
                ],
            }
        )
        self.activity_type_no_auto = ActivityType.create(
            {
                "name": "Call for Demo",
                "delay_count": 6,
                "delay_unit": "days",
                "summary": "ACT 2 : I want to show you my ERP !",
                "res_model": self.partner_model.model,
            }
        )

        self.partner_client = self.env.ref("base.res_partner_1")

        # assure there isn't any mail activity yet
        self.env["mail.activity"].sudo().search([]).unlink()

    def test_create_activity_auto(self):
        """This test case checks
        - If create acivity with type auto create queue job.
        """
        activity = (
            self.env["mail.activity"]
            .sudo()
            .create(
                {
                    "activity_type_id": self.activity_type_auto.id,
                    "note": "Partner activity Auto.",
                    "res_id": self.partner_client.id,
                    "res_model_id": self.partner_model.id,
                }
            )
        )

        jobs = activity.activity_jobs_ids

        self.assertTrue(jobs and True)

    def test_create_activity_no_auto(self):
        """This test case checks
        - If create acivity with type auto create queue job.
        """
        activity = (
            self.env["mail.activity"]
            .sudo()
            .create(
                {
                    "activity_type_id": self.activity_type_no_auto.id,
                    "note": "Partner activity Auto.",
                    "res_id": self.partner_client.id,
                    "res_model_id": self.partner_model.id,
                }
            )
        )

        jobs = activity.activity_jobs_ids

        self.assertFalse(jobs or False)

    def test_create_activity_no_auto_action(self):
        """This test case checks
        - If create acivity with type no auto:
          - No create queue job.
          - Execute action when set activity as done.
        """
        activity = (
            self.env["mail.activity"]
            .sudo()
            .create(
                {
                    "activity_type_id": self.activity_type_no_auto_action.id,
                    "note": "Partner activity Auto.",
                    "res_id": self.partner_client.id,
                    "res_model_id": self.partner_model.id,
                }
            )
        )

        jobs = activity.activity_jobs_ids

        self.assertFalse(jobs or False)

        self.partner_client.active = True

        self.assertTrue(self.partner_client.active)

        activity.do_automated_action()

        self.assertFalse(self.partner_client.active)

    def test_execute_action(self):
        """This test case checks
        - if the method execute auto action.
        """
        self.partner_client.active = True

        self.assertTrue(self.partner_client.active)

        activity = (
            self.env["mail.activity"]
            .sudo()
            .create(
                {
                    "activity_type_id": self.activity_type_auto.id,
                    "note": "Partner activity Auto.",
                    "res_id": self.partner_client.id,
                    "res_model_id": self.partner_model.id,
                }
            )
        )

        activity.do_automated_action()

        self.assertFalse(self.partner_client.active)

    def test_domain_no_execute_action(self):
        """This test case checks
        - if the domain is false then method do not execute auto action.
        """
        self.partner_client.active = True

        self.assertTrue(self.partner_client.active)

        self.partner_client.is_company = False

        self.assertFalse(self.partner_client.is_company)

        activity = (
            self.env["mail.activity"]
            .sudo()
            .create(
                {
                    "activity_type_id": self.activity_type_auto.id,
                    "note": "Partner activity Auto.",
                    "res_id": self.partner_client.id,
                    "res_model_id": self.partner_model.id,
                }
            )
        )

        activity.do_automated_action()

        self.assertTrue(self.partner_client.active)

    def test_unlink_activity_auto(self):
        """This test case checks
        - If delete acivity with type auto related queue job set to done.
        """
        activity = (
            self.env["mail.activity"]
            .sudo()
            .create(
                {
                    "activity_type_id": self.activity_type_auto.id,
                    "note": "Partner activity Auto.",
                    "res_id": self.partner_client.id,
                    "res_model_id": self.partner_model.id,
                }
            )
        )

        jobs = activity.activity_jobs_ids

        self.assertTrue(jobs and True)

        activity.sudo().unlink()

        for job in jobs:
            self.assertEqual(job.state, "done")

    def test_done_activity_auto(self):
        """This test case checks
        - If set acivity with type auto to done execute related queue job.
        """
        activity = (
            self.env["mail.activity"]
            .sudo()
            .create(
                {
                    "activity_type_id": self.activity_type_auto.id,
                    "note": "Partner activity Auto.",
                    "res_id": self.partner_client.id,
                    "res_model_id": self.partner_model.id,
                }
            )
        )

        jobs = activity.activity_jobs_ids

        self.assertTrue(jobs and True)

        activity.action_done()

        for job in jobs:
            self.assertFalse(job.eta)

    def test_update_activity_auto(self):
        """This test case checks
        - If update date or time of acivity with type auto update related queue job.
        """
        activity = (
            self.env["mail.activity"]
            .sudo()
            .create(
                {
                    "activity_type_id": self.activity_type_auto.id,
                    "note": "Partner activity Auto.",
                    "res_id": self.partner_client.id,
                    "res_model_id": self.partner_model.id,
                }
            )
        )

        jobs = activity.activity_jobs_ids

        self.assertTrue(jobs and True)

        activity.date_deadline = fields.Date.to_date("2022-01-01")
        eta = activity._get_auto_eta()

        for job in jobs:
            self.assertEqual(job.eta, eta)
