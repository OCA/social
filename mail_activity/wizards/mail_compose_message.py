# -*- coding: utf-8 -*-
from openerp import fields, models


class MailComposer(models.TransientModel):

    _inherit = 'mail.compose.message'

    # This field is already in v10 onwards.
    subtype_id = fields.Many2one(
        default=lambda self: self.sudo().env.ref('mail.mt_comment',
                                                 raise_if_not_found=False).id)
