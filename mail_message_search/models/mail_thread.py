# Copyright 2016-17 ForgeFlow S.L.
#   (http://www.forgeflow.com)
# Copyright 2016 Serpent Consulting Services Pvt. Ltd.
#   (<http://www.serpentcs.com>)
# Copyright 2025 Quartile (https://www.quartile.co)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from lxml import etree

from odoo import api, fields, models
from odoo.osv import expression


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    def _search_message_search(self, operator, value):
        fields = ["record_name", "subject", "body", "email_from", "reply_to"]
        words = value.split()
        word_domain_list = []
        for word in words:
            field_domain_list = [[(field, operator, word)] for field in fields]
            if operator in expression.NEGATIVE_TERM_OPERATORS:
                word_domain_list.append(expression.AND(field_domain_list))
            else:
                word_domain_list.append(expression.OR(field_domain_list))
        word_domain = expression.AND(word_domain_list)
        domain = expression.AND([[("model", "=", self._name)], word_domain])
        messages = self.env["mail.message"].search(domain)
        return [("id", "in", messages.mapped("res_id"))]

    message_search = fields.Text(
        help="Message search, to be used only in searches",
        compute="_compute_message_search",
        search="_search_message_search",
    )

    def _compute_message_search(self):
        # Always assign a value to avoid CacheMiss errors
        self.message_search = False

    @api.model
    def get_view(self, view_id=None, view_type="form", **options):
        """
        Override to add message_search field in all the objects
        that inherits mail.thread
        """
        res = super().get_view(view_id=view_id, view_type=view_type, options=options)
        if (
            view_type == "search"
            and self._fields.get("message_search")
            and self.env.user.has_group("base.group_user")
        ):
            doc = etree.XML(res["arch"])
            for node in doc.xpath("/search/field[last()]"):
                # Add message_search in search view
                elem = etree.Element("field", {"name": "message_search"})
                node.addnext(elem)
                res["arch"] = etree.tostring(doc)
        return res
