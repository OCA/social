# -*- coding: utf-8 -*-
# © 2017 Sunflower IT (http://sunflowerweb.nl)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import logging
from openerp import _, api, models, tools
from openerp.tools import html_email_clean
from openerp.tools.translate import _
from HTMLParser import HTMLParser
from openerp import SUPERUSER_ID, api
_logger = logging.getLogger(__name__)


class MailMessage(models.Model):
    _inherit = 'mail.message'

    def _message_read_dict(self, cr, uid, message, parent_id=False,
                           context=None):
        max_length = 10000 # Increase the max lenght
        body_short = html_email_clean(message.body, remove=False, shorten=False,
                                      max_length=max_length) # Disable shortening
        ret = super(MailMessage, self)._message_read_dict(cr, uid,
                                                           message,
                                                           parent_id=parent_id,
                                                           context=context)
        ret['body_short'] = body_short
        return ret


