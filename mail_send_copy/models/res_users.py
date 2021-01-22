# Copyright (C) 2014 - Today: GRAP (http://www.grap.coop)
# @author: Sylvain LE GAL (https://twitter.com/legalsylvain)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    mail_send_copy = fields.Boolean(
        string="Send Email Copy", default=True,
        help="If checked, you will receive each mail in bcc mode"
        " for each mail you will send using Odoo.")

    def __init__(self, pool, cr):
        """ Override of __init__ to add access rights.
        Access rights are disabled by default, but allowed on some specific
        fields defined in self.SELF_WRITEABLE_FIELDS.
        """
        super().__init__(pool, cr)
        # duplicate list to avoid modifying the original reference
        type(self).SELF_WRITEABLE_FIELDS = list(self.SELF_WRITEABLE_FIELDS)
        type(self).SELF_WRITEABLE_FIELDS.extend(['mail_send_copy'])
