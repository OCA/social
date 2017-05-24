# -*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2016 Compassion CH (http://www.compassion.ch)
#    Releasing children from poverty in Jesus' name
#    @author: Emanuel Cino <ecino@compassion.ch>
#
#    The licence is in the file __openerp__.py
#
##############################################################################
from openerp import models, fields, api


class MailTrackingEmail(models.Model):
    """ Count the user clicks on links inside e-mails sent.
    """
    _inherit = 'mail.tracking.email'

    click_count = fields.Integer(compute='_compute_clicks', store=True)

    @api.depends('tracking_event_ids')
    def _compute_clicks(self):
        for mail in self:
            mail.click_count = len(mail.tracking_event_ids.filtered(
                lambda event: event.event_type == 'click'))
