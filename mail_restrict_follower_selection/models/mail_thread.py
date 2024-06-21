from odoo import models
from odoo.tools import config
from odoo.tools.safe_eval import safe_eval

from ..utils import _id_get


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    def _message_add_suggested_recipient(
        self, result, partner=None, email=None, reason=""
    ):
        result = super()._message_add_suggested_recipient(
            result, partner=partner, email=email, reason=reason
        )
        test_condition = config["test_enable"] and not self.env.context.get(
            "test_restrict_follower"
        )
        if test_condition or self.env.context.get("no_restrict_follower"):
            return result
        domain = self.env[
            "mail.wizard.invite"
        ]._mail_restrict_follower_selection_get_domain()
        eval_domain = safe_eval(
            domain, locals_dict={"ref": lambda str_id: _id_get(self.env, str_id)}
        )
        for key in result:
            for partner_id, email, reason in result[key]:
                if partner_id:
                    partner = self.env["res.partner"].search(
                        [("id", "=", partner_id)] + eval_domain
                    )
                    if not partner:
                        result[key].remove((partner_id, email, reason))
        return result
