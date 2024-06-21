# Copyright (C) 2018 Creu Blanca
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models
from odoo.tools import config
from odoo.tools.safe_eval import safe_eval

from ..utils import _id_get


class MailFollowers(models.Model):
    _inherit = "mail.followers"

    def _add_followers(
        self,
        res_model,
        res_ids,
        partner_ids,
        partner_subtypes,
        channel_ids,
        channel_subtypes,
        check_existing=False,
        existing_policy="skip",
    ):
        test_condition = config["test_enable"] and not self.env.context.get(
            "test_restrict_follower"
        )
        if test_condition or self.env.context.get("no_restrict_follower"):
            return super()._add_followers(
                res_model,
                res_ids,
                partner_ids,
                partner_subtypes,
                channel_ids,
                channel_subtypes,
                check_existing=check_existing,
                existing_policy=existing_policy,
            )
        domain = self.env[
            "mail.wizard.invite"
        ]._mail_restrict_follower_selection_get_domain(res_model=res_model)
        partners = self.env["res.partner"].search(
            [("id", "in", partner_ids)]
            + safe_eval(
                domain, locals_dict={"ref": lambda str_id: _id_get(self.env, str_id)}
            )
        )
        _res_ids = res_ids.copy() or [0]
        new, update = super()._add_followers(
            res_model,
            res_ids,
            partners.ids,
            partner_subtypes,
            channel_ids,
            channel_subtypes,
            check_existing=check_existing,
            existing_policy=existing_policy,
        )

        for res_id in _res_ids:
            if res_id not in new:
                new.setdefault(res_id, list())
        return new, update
