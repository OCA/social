from openerp import api, models

import logging
_logger = logging.getLogger(__name__)

class MailChannel(models.Model):
    _inherit = "mail.channel"

    @api.multi
    def channel_info(self, extra_info=False):
        method_return = super(MailChannel, self).channel_info(extra_info)
        _logger.info(str(method_return))
        _logger.info(method_return[0]['operator_pid'])
        method_return[0]['operator_pid'] = (1, "TEST!")
        _logger.info(method_return[0]['operator_pid'])
        
        return method_return
