# Copyright 2016-22 PESOL
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
import logging

from odoo import api, fields, models
from odoo.tools import safe_eval

_logger = logging.getLogger(__name__)
try:
    from odoo.addons.queue_job.job import job
except ImportError:
    _logger.debug("Can not `import queue_job`.")
    import functools

    def empty_decorator_factory(*argv, **kwargs):
        return functools.partial

    job = empty_decorator_factory


class MailActivity(models.Model):
    _inherit = "mail.activity"

    @api.model
    def _get_default_time(self):
        return 0

    time_deadline = fields.Float(
        string="Due Time", required=True, default=_get_default_time
    )

    activity_jobs_ids = fields.Many2many(
        comodel_name="queue.job",
        column1="activity_id",
        column2="job_id",
        relation="mail_activity_queue_job_rel",
        string="Queue Jobs",
        copy=False,
    )

    @api.model
    def create(self, vals):
        res = super(MailActivity, self).create(vals)
        res._queue_automated_actions()
        return res

    def unlink(self):
        queue_jobs = self.activity_jobs_ids.filtered(
            lambda a: a.state in ["pending", "failed"]
        )
        queue_jobs.button_done()
        return super(MailActivity, self).unlink()

    def _action_done(self, feedback=False, attachment_ids=None):
        if self.activity_type_id.auto:
            self.activity_jobs_ids.filtered(lambda a: a.state == "pending").write(
                {"eta": False}
            )
        else:
            self.execute_action()
        return super(MailActivity, self)._action_done(
            feedback=feedback, attachment_ids=attachment_ids
        )

    def write(self, vals):
        res = super(MailActivity, self).write(vals)
        if ("date_deadline" in vals) or ("time_deadline" in vals):
            eta = self._get_auto_eta()
            self.activity_jobs_ids.filtered(lambda a: a.state in ["pending"]).write(
                {"eta": eta}
            )
        return res

    def execute_action(self):
        eval_context = {
            "datetime": safe_eval.datetime,
            "dateutil": safe_eval.dateutil,
            "time": safe_eval.time,
            "uid": self.env.uid,
            "user": self.env.user,
        }
        for record in self.filtered(lambda a: a.activity_type_id.auto_action_ids):
            res = self.env[record.res_model].browse(record.res_id)

            for action in record.activity_type_id.auto_action_ids:
                if action.filter_domain:
                    domain = safe_eval.safe_eval(action.filter_domain, eval_context)
                    res = res.filtered_domain(domain)
                if res:
                    action = action.auto_action_id
                    action.with_context(
                        active_id=record.res_id,
                        model_id=record.res_model_id.id,
                        res_model=record.res_model,
                        active_model=record.res_model,
                    ).run()

    def do_automated_action(self):
        self.ensure_one()
        self.execute_action()
        if self.activity_type_id.auto:
            return super(MailActivity, self)._action_done()

    def _get_auto_eta(self):
        hour, minute = divmod(self.time_deadline * 60, 60)
        hour = int(hour)
        minute = int(minute)
        datetime_deadline = fields.Datetime.to_datetime(self.date_deadline)
        datetime_deadline = datetime_deadline.replace(hour=hour, minute=minute)
        return datetime_deadline

    def _queue_automated_actions(self):
        queue_obj = self.env["queue.job"].sudo()
        for action in self.filtered(lambda a: a.activity_type_id.auto):
            eta = action._get_auto_eta()
            new_delay = action.sudo().with_delay(eta=eta).do_automated_action()
            job = queue_obj.search([("uuid", "=", new_delay.uuid)], limit=1)
            action.sudo().activity_jobs_ids |= job
