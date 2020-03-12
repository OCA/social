# Copyright 2019 Druidoo - Iván Todorovich <ivan.todorovich@druidoo.io>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, models, fields
from odoo.tools import safe_eval
import datetime
import time
import dateutil


class MailTemplateConditionalAttachment(models.Model):
    _name = 'mail.template.conditional.attachment'
    _description = 'Mail Template Conditional Attachment'

    name = fields.Char('Description', required=True)
    mail_template_id = fields.Many2one(
        'mail.template',
        ondelete='cascade',
        required=True,
    )
    attachment_ids = fields.Many2many(
        'ir.attachment',
        string='Attachments',
    )
    filter_domain = fields.Char(
        'Apply on',
        help='If present, this condition must be satisfied '
             'to include the attachments.',
    )
    model_name = fields.Char(related='mail_template_id.model_id.model')

    def _get_eval_context(self):
        return {
            'datetime': datetime,
            'dateutil': dateutil,
            'time': time,
            'uid': self.env.uid,
            'user': self.env.user,
        }

    def _check_condition(self, res_id):
        """
        Checks if the conditions are satisfied for the specified record.

        :param res_id: id of the record to use, usually the record for
                       rendering the template (model is taken from template
                       definition)
        """
        self.ensure_one()
        if not self.filter_domain:
            return True
        domain = [('id', '=', res_id)]
        domain += safe_eval(self.filter_domain, self._get_eval_context())
        model = self.env[self.model_name]
        return bool(model.search_count(domain))

    @api.multi
    def get_attachments(self, res_id):
        """
        Returns all conditional attachments that satisfies the conditions
        for the specficied record.

        :param res_id: id of the record to use, usually the record for
                       rendering the template (model is taken from template
                       definition)
        """
        self.mapped('mail_template_id').ensure_one()
        return self.filtered(
            lambda r: r._check_condition(res_id)).mapped('attachment_ids')
