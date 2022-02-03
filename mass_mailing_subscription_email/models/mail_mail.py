# Copyright 2022 Camptocamp SA (https://www.camptocamp.com).
# @author Iván Todorovich <ivan.todorovich@camptocamp.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class MailMail(models.Model):
    _inherit = "mail.mail"

    def _send_prepare_values(self, partner=None):
        # OVERRIDE to replace /unsubscribe_from_list url
        res = super()._send_prepare_values(partner)
        if self.model == "mailing.contact.subscription":
            subscription = self.env["mailing.contact.subscription"].browse(self.res_id)
            url_to_replace = "/unsubscribe_from_list"
            url_to_replace_with = subscription._get_unsubscribe_url() or "#"
            if url_to_replace in res["body"]:
                res["body"] = res["body"].replace(url_to_replace, url_to_replace_with)
        return res
