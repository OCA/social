# -*- coding: utf-8 -*-
# Python source code encoding : https://www.python.org/dev/peps/pep-0263/
##############################################################################
# For copyright and license notices, see __openerp__.py file in root directory
##############################################################################

import urlparse
import urllib

from openerp import models
from openerp.tools.translate import _


class MailMail(models.Model):
    _inherit = 'mail.mail'

    def _get_unsubscribe_url(self, cr, uid, mail, email_to,
                             msg=None, context=None):
        m_config = self.pool.get('ir.config_parameter')
        base_url = m_config.get_param(cr, uid, 'web.base.url')
        config_msg = m_config.get_param(cr, uid,
                                        'mass_mailing.unsubscribe.label')
        url = urlparse.urljoin(
            base_url, 'mail/mailing/%(mailing_id)s/unsubscribe?%(params)s' % {
                'mailing_id': mail.mailing_id.id,
                'params': urllib.urlencode({
                    'db': cr.dbname,
                    'res_id': mail.res_id,
                    'email': email_to
                })
            }
        )
        html = ''
        if config_msg is False:
            html = '<small><a href="%(url)s">%(label)s</a></small>' % {
                'url': url,
                'label': msg or _('Click to unsubscribe'),
            }
        elif config_msg.lower() != 'false':
            html = config_msg % {
                'url': url,
            }
        return html
