# Copyright 2025 Quartile (https://www.quartile.co)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging

from odoo import api, models
from odoo.tools import safe_eval

_logger = logging.getLogger(__name__)


class MailMessage(models.Model):
    _inherit = "mail.message"

    def _get_reply_stage(self, res, config):
        self.ensure_one()
        reply_stage = self.env[config.reply_stage_model_name].search(
            [("id", "=", config.reply_stage_id)]
        )
        if config.parent_stage_field_id:
            parent_field_rec = getattr(res, config.parent_field_id.name, None)
            allowed_stages = getattr(
                parent_field_rec,
                config.parent_stage_field_id.name,
                self.env[config.parent_stage_field_id.relation],
            )
            reply_stage = reply_stage.filtered(lambda stage: stage in allowed_stages)
        return reply_stage

    def _get_mail_reply_config(self, res, res_model):
        self.ensure_one()
        configs = self.env["mail.reply.config"].search(
            [("model_id", "=", res_model.id)], order="sequence ASC"
        )
        for config in configs:
            reply_stage = self._get_reply_stage(res, config)
            if not reply_stage:
                continue
            domain = []
            if config.domain:
                try:
                    domain = safe_eval.safe_eval(config.domain)
                except Exception as e:
                    _logger.warning("Invalid domain: %s (%s)", config.domain, e)
                    continue
            if not domain or res.filtered_domain(domain):
                return config, reply_stage
        return None, None

    @api.model_create_multi
    def create(self, values_list):
        messages = super().create(values_list)
        for message in messages:
            user = message.author_id.user_ids[:1]
            if user and user.has_group("base.group_user"):
                continue
            if message.subtype_id and message.subtype_id.internal:
                continue
            res_model = (
                self.env["ir.model"]
                .sudo()
                .search([("model", "=", message.model)], limit=1)
            )
            if not res_model:
                continue
            res = self.env[message.model].browse(message.res_id)
            config, reply_stage = message._get_mail_reply_config(res, res_model)
            if not config:
                continue
            if reply_stage:
                res.sudo().write({config.reply_stage_field_id.name: reply_stage.id})
        return messages
