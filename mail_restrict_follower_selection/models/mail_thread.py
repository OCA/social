from odoo import models
from odoo.tools import config


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    def _message_add_suggested_recipient(
        self, result, partner=None, email=None, lang=None, reason=""
    ):
        result = super()._message_add_suggested_recipient(
            result, partner=partner, email=email, lang=lang, reason=reason
        )
        test_condition = config["test_enable"] and not self.env.context.get(
            "test_restrict_follower"
        )
        if test_condition or self.env.context.get("no_restrict_follower"):
            return result
        domain = self.env[
            "mail.wizard.invite"
        ]._mail_restrict_follower_selection_get_domain()
        for key in result:
            items_to_remove = []
            for item in result[key]:
                partner_id = item[0]
                if partner_id:
                    partner = self.env["res.partner"].search_count(
                        [("id", "=", partner_id)] + domain
                    )
                    if not partner:
                        items_to_remove.append(item)
            for item in items_to_remove:
                result[key].remove(item)
        return result
