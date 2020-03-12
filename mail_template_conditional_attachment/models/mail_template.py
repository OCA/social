# Copyright 2019 Druidoo - Iván Todorovich <ivan.todorovich@druidoo.io>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, models, fields
from odoo.tools import pycompat


class MailTemplate(models.Model):
    _inherit = 'mail.template'

    conditional_attachment_ids = fields.One2many(
        'mail.template.conditional.attachment',
        'mail_template_id',
        string='Conditional Attachments',
    )

    @api.multi
    def generate_email(self, res_ids, **kwargs):
        self.ensure_one()
        # Odoo way of handling different result for multi/one res_ids
        # Placed before super(), so we force multi_mode=True there
        multi_mode = True
        if isinstance(res_ids, pycompat.integer_types):
            res_ids = [res_ids]
            multi_mode = False

        results = super().generate_email(res_ids, **kwargs)
        # Add conditional attachments
        if self.conditional_attachment_ids:
            for res_id in res_ids:
                attachment_ids = \
                    self.conditional_attachment_ids.get_attachments(res_id)
                results[res_id]['attachment_ids'] = attachment_ids.ids
        return multi_mode and results or results[res_ids[0]]
