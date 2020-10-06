# Copyright 2016-17 Eficent Business and IT Consulting Services S.L.
#   (http://www.eficent.com)
# Copyright 2016 Serpent Consulting Services Pvt. Ltd.
#   (<http://www.serpentcs.com>)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from lxml import etree

from odoo import _, api, fields, models
from odoo.osv import expression


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    def _search_message_content(self, operator, value):
        model_domain = [("model", "=", self._name)]
        if operator not in expression.NEGATIVE_TERM_OPERATORS:
            model_domain += ["|"] * 4
        model_domain += [
            ("record_name", operator, value),
            ("subject", operator, value),
            ("body", operator, value),
            ("email_from", operator, value),
            ("reply_to", operator, value),
        ]
        recs = self.env["mail.message"].search(model_domain)
        return [("id", "in", recs.mapped("res_id"))]

    message_content = fields.Text(
        string="Message Content",
        help="Message content, to be used only in searches",
        compute=lambda self: False,
        search="_search_message_content",
    )

    @api.model
    def fields_view_get(
        self, view_id=None, view_type="form", toolbar=False, submenu=False
    ):
        """
        Override to add message_content field in all the objects
        that inherits mail.thread
        """
        res = super(MailThread, self).fields_view_get(
            view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu
        )
        if view_type == "search" and self._fields.get("message_content"):
            doc = etree.XML(res["arch"])
            res["fields"].update(
                {"message_content": {"type": "char", "string": _("Message Content")}}
            )
            for node in doc.xpath("/search/field[last()]"):
                # Add message_content in search view
                elem = etree.Element("field", {"name": "message_content"})
                node.addnext(elem)
                res["arch"] = etree.tostring(doc)
        return res
