# -*- coding: utf-8 -*-
# Copyright 2019 Therp BV <https://therp.nl>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
import uuid
import logging
from odoo import models, http
from odoo.addons.base.ir.ir_mail_server import encode_header_param
from werkzeug.wrappers import Request
from werkzeug.test import EnvironBuilder
from lxml.html.soupparser import fromstring
from lxml.etree import tostring
from base64 import encodebytes
from email.mime.image import MIMEImage
from odoo.http import root as root_wsgi
import threading


logger = logging.getLogger(__name__)


class IrMailServer(models.Model):
    _inherit = 'ir.mail_server'

    def build_email(
            self,
            email_from,
            email_to,
            subject,
            body,
            email_cc=None,
            email_bcc=None,
            reply_to=None,
            attachments=None,
            message_id=None,
            references=None,
            object_id=None,
            subtype='plain',
            headers=None,
            body_alternative=None,
            subtype_alternative='plain'):
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
        base_url = self.env['ir.config_parameter'].get_param(
            'web.base.url')
        for part in email.walk():
            if part.get_content_maintype() == 'text':
                body = part.get_payload(decode=True)
                if not body or body == '\n':
                    continue
                root = fromstring(body)
                for img in root.xpath(
                        "//img[starts-with(@src, '%s/web/image')]"
                        "|"
                        "//img[starts-with(@src, '/web/image')]" % (
                            base_url or '', )):
                    # check if there is a bound request
                    imgpath = img.get('src').replace(base_url, '')
                    env = EnvironBuilder(imgpath).get_environ()
                    endpoint, arguments = http.routing_map(
                        self.env.registry._init_modules,
                        False,
                        self.env['ir.http']._get_converters(),
                    ).bind_to_environ(
                        env,
                    ).match(return_rule=False)
                    try:
                        req = http.request.pop()
                    except RuntimeError:
                        # if there is not one, just create a fake one
                        req = Request(env)
                        # setup session
                        session_store = root_wsgi.session_store
                        session = session_store.new()
                        session.update({
                            'db': threading.current_thread().dbname,
                            'login': self.env.user.login,
                            'uid': self.env.user.id,
                            'content': self.env.context,
                            })
                        req.session = session
                        req = http.HttpRequest(req)
                        http._request_stack.push(req)
                    # now go ahead and call the endpoint and fetch the data
                    response = endpoint.method(**arguments)
                    if not response:
                        logger.warning('Could not get %s', img.get('src'))
                        continue
                    cid = uuid.uuid4().hex
                    filename_rfc2047 = encode_header_param(cid)
                    filepart = MIMEImage(response.data)
                    filepart.set_param('name', filename_rfc2047)
                    filepart.add_header(
                        'Content-Disposition',
                        'inline',
                        cid=cid,
                        filename=filename_rfc2047,
                    )
                    # attach the image into the email as attachment
                    email.attach(filepart)
                    img.set('src', 'cid:%s' % (cid))
                # encodebytes will put a newline every 74 char
                part.set_payload(encodebytes(tostring(root)))
        return email
