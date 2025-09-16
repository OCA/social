# Copyright 2021 Camptocamp (http://www.camptocamp.com).
# @author Iván Todorovich <ivan.todorovich@gmail.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class MailTemplate(models.Model):
    _inherit = "mail.template"

    use_autosubscribe_followers = fields.Boolean(default=True)

    def _generate_template_recipients(
        self, res_ids, render_fields, find_or_create_partners=False, render_results=None
    ):
        res = super()._generate_template_recipients(
            res_ids, render_fields, find_or_create_partners, render_results
        )
        autosubscribe_followers = (
            self.use_autosubscribe_followers
            and not self.env.context.get("no_autosubscribe_followers")
            # In this case, autosubscribers will be added by
            # :func:`_message_get_default_recipients`
            and not self.use_default_to
        )
        if autosubscribe_followers:
            for res_id, values in res.items():
                partner_ids = values.get("partner_ids")
                if not partner_ids:
                    continue
                partners = self.env["res.partner"].sudo().browse(partner_ids)
                ResModel = self.env[self.model]
                followers = ResModel._message_get_autosubscribe_followers(partners)
                follower_ids = [
                    follower.id for follower in followers if follower not in partners
                ]
                res[res_id]["partner_ids"] += follower_ids
        return res
