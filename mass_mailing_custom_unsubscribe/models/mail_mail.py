# -*- coding: utf-8 -*-
# Python source code encoding : https://www.python.org/dev/peps/pep-0263/
##############################################################################
# For copyright and license notices, see __openerp__.py file in root directory
##############################################################################

import urlparse
import urllib
from openerp import api, models
from openerp.tools.translate import _


class MailMail(models.Model):
    _inherit = 'mail.mail'

    @api.model
    def _get_unsubscribe_url(self, mail, email_to, msg=None):
        m_config = self.env['ir.config_parameter']
        base_url = m_config.get_param('web.base.url')
        config_msg = m_config.get_param('mass_mailing.unsubscribe.label')
        params = {
            'db': self.env.cr.dbname,
            'res_id': mail.res_id,
            'email': email_to,
            'token': self.env["mail.mass_mailing"].hash_create(
                mail.mailing_id.id,
                mail.res_id,
                email_to),
        }

        # Avoid `token=None` in URL
        if not params["token"]:
            del params["token"]

        # Generate URL
        url = urlparse.urljoin(
            base_url, 'mail/mailing/%(mailing_id)s/unsubscribe?%(params)s' % {
                'mailing_id': mail.mailing_id.id,
                'params': urllib.urlencode(params),
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
