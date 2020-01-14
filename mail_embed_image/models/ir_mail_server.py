# -*- coding: utf-8 -*-
# Copyright 2019 Therp BV <https://therp.nl>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
import uuid
import logging
from contextlib import contextmanager
from odoo import models, http
from odoo.addons.base.ir.ir_mail_server import encode_header_param
from werkzeug.test import EnvironBuilder
from werkzeug.wrappers import Request as WerkzeugRequest
from lxml.html.soupparser import fromstring
from lxml.etree import tostring
from base64 import encodestring
import threading
from odoo.http import root as root_wsgi
from email.mime.image import MIMEImage


logger = logging.getLogger(__name__)


class IrMailServer(models.Model):
    _inherit = 'ir.mail_server'

    @contextmanager
    def _fetch_image(self, path):
        public_user = self.env.ref('base.public_user')
        session_store = root_wsgi.session_store
        session = session_store.new()
        session.update({
            'db': threading.current_thread().dbname,
            'login': public_user.login,
            'uid': public_user.id,
            'context': self.env.context,
            })
        werkzeug_env = EnvironBuilder(path).get_environ()
        werkzeug_request = WerkzeugRequest(werkzeug_env)
        werkzeug_request.session = session
        # construct an odoo request with this werkzeug request.
        request = http.HttpRequest(werkzeug_request)
        with request:
            request._env = self.env(user=public_user)
            endpoint, arguments = http.routing_map(
                self.env.registry._init_modules,
                False,
                self.env['ir.http']._get_converters()
            ).bind_to_environ(
                werkzeug_env).match(return_rule=False,)
            yield endpoint, arguments

    def build_email(
            self,
            email_from,
            email_to,
            subject,
            body,
            email_cc=None,
            email_bcc=None,
            reply_to=False,
            attachments=None,
            message_id=None,
            references=None,
            object_id=False,
            subtype='plain',
            headers=None,
            body_alternative=None,
            subtype_alternative='plain',
    ):
        result = super(IrMailServer, self).build_email(
            email_from=email_from,
            email_to=email_to,
            subject=subject,
            body=body,
            email_cc=email_cc,
            email_bcc=email_bcc,
            reply_to=reply_to,
            attachments=attachments,
            message_id=message_id,
            references=references,
            object_id=object_id,
            subtype=subtype,
            headers=headers,
            body_alternative=body_alternative,
            subtype_alternative=subtype_alternative,
        )
        return self._build_email_replace_img_src(result)

    def _build_email_replace_img_src(self, email):
        """ Given a message, find it's img tags and if they
        are URLs, replace them with cids.
        """
        for part in email.walk():
            if part.get_content_type() == 'text/html':
                body = part.get_payload(decode=True)
                if not body or body == '\n':
                    continue
                root = self._build_email_process_img_body(
                    fromstring(body), email)
                # encodestring will put a newline every 74 char
                part.set_payload(encodestring(tostring(root)))
        return email

    def _build_email_process_img_body(self, root, email):
        base_url = self.env['ir.config_parameter'].get_param(
            'web.base.url')
        for img in root.xpath(
                ".//img[starts-with(@src, '%s/web/image')]"
                "| .//img[starts-with(@src, '/web/image')]" % (base_url)):
            image_path = img.get('src').replace(base_url, '')
            with self._fetch_image(image_path) as (endpoint, arguments):
                # now go ahead and call the endpoint and fetch the data
                response = endpoint.method(**arguments)
                if not response or response.status_code != 200:
                    logger.warning('Could not get %s', img.get('src'))
                    continue
                cid = uuid.uuid4().hex
                filename_rfc2047 = encode_header_param(cid)
                filepart = MIMEImage(response.data)
                # TODO check if filepart exists (do not attach twice)
                filepart.set_param('name', filename_rfc2047)
                filepart.add_header(
                    'Content-Disposition',
                    'inline',
                    cid=cid,
                    filename=filename_rfc2047,
                )
                # attach the image into the email as attachment
                email.attach(filepart)
                img.set('src', 'cid:%s' % (str(cid)))
        return root
