# -*- coding: utf-8 -*-
import logging
import re
import imaplib
from odoo import tools
from odoo.exceptions import ValidationError
from odoo import fields
from odoo import models
from odoo import api
from odoo.tools.translate import _

_logger = logging.getLogger(__name__)


class IrMailServer(models.Model):
    _inherit = 'ir.mail_server'

    def parse_list_response(self, line):
        list_response_pattern = re.compile(
            r'\((?P<flags>.*?)\) "(?P<delimiter>.*)" (?P<name>.*)'
        )
        flags, delimiter, mailbox_name = \
            list_response_pattern.match(line).groups()
        mailbox_name = mailbox_name.strip('"')
        return (flags, delimiter, mailbox_name)

    @api.multi
    def test_imap_connection(self):
        self.ensure_one()
        imap_pool = self.env['ir.mail.imap.folder']
        if self.has_separate_imap_server:
            smtp_server = self.separate_imap_server
        else:
            smtp_server = self.smtp_host
        try:
            maillib = imaplib.IMAP4_SSL(smtp_server)
            result = maillib.login(self.smtp_user, self.smtp_pass)
            typ, mBoxes = maillib.list()
            folder_ids = imap_pool.search([('server_id', '=', self.id)])
            for folder in folder_ids:
                folder.unlink()
            for line in mBoxes:
                flags, delimiter, mailbox_name = self.parse_list_response(line)
                res = {
                    'server_id': self.id,
                    'name': mailbox_name,
                }
                imap_pool.create(res)
            self.write({'imap_mailbox_verified': True})
        except Exception, e:
            raise ValidationError(
                _("Connection Test Failed!"
                "Here is what we got instead:\n %s") % tools.ustr(e))
        finally:
            try:
                if result:
                    maillib.logout()
            except Exception:
                # ignored, just a consequence of the previous exception
                pass

    @api.model
    def send_email(self, message, mail_server_id=None,
                   smtp_server=None, smtp_port=None, smtp_user=None,
                   smtp_password=None, smtp_encryption=None, smtp_debug=False):
        super(IrMailServer, self).send_email(
            message, mail_server_id, smtp_server, smtp_port,
            smtp_user, smtp_password, smtp_encryption, smtp_debug)
        return self._save_sent_message_to_sentbox(message, mail_server_id)

    @api.model
    def _save_sent_message_to_sentbox(self, msg, mail_server_id,):
        smtp_server = None
        ir_mail_server = self.env['ir.mail_server']
        mail_server = None
        mail_server = ir_mail_server.sudo().search([], order='sequence',
                                                   limit=1)
        if mail_server:
            if not mail_server.store_outgoing_mail:
                return True
            if mail_server.has_separate_imap_server:
                smtp_server = mail_server.separate_imap_server
            else:
                smtp_server = mail_server.smtp_host
            smtp_user = mail_server.smtp_user
            smtp_password = mail_server.smtp_pass
        if not smtp_server:
            raise ValidationError(_(
                "Please define at least one SMTP server, or provide the"
                " SMTP parameters explicitly."))
        maillib = imaplib.IMAP4_SSL(smtp_server)
        try:
            maillib.login(smtp_user, smtp_password)
            folder = mail_server.imap_mailbox_folder.name.join('""')
            maillib.append(folder, r'\Seen', None, str(msg))
        except Exception, ex:
                _logger.error(_(
                    'Failed attaching mail via imap to server %s %s')
                    % (ex, msg))
        finally:
            maillib.logout()
        return True

    imap_mailbox_folder = fields.Many2one('ir.mail.imap.folder',
                                          'Imap Folders',)
    imap_mailbox_verified = fields.Boolean('IMAP Connection Verified', )
    store_outgoing_mail = fields.Boolean('Store Outgoing Mail', )
    has_separate_imap_server = fields.Boolean('Use Separate Imap Server', )
    separate_imap_server = fields.Char('Separate Imap Server', )
    active = fields.Boolean('Active', )


class IrMailImapFolder(models.Model):
    _name = 'ir.mail.imap.folder'
    _description = 'Imap Folder'

    server_id = fields.Many2one('ir.mail_server', 'Mail Server', )
    name = fields.Char('Foldername',)
