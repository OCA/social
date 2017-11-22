# -*- coding: utf-8 -*-
# Copyright 2017 Tecnativa - Pedro M. Baeza
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).


from odoo import _, exceptions, models


class MailMassMailingList(models.Model):
    _inherit = "mail.mass_mailing"

    def button_draft(self):
        """Return to draft state for resending the mass mailing."""
        if any(self.mapped(lambda x: x.state != 'done')):
            raise exceptions.UserError(
                _("You can't resend a mass mailing that is being sent or in "
                  "draft state.")
            )
        self.write({'state': 'draft'})
