# -*- coding: utf-8 -*-

import logging
from odoo import models, fields, api, _

_logger = logging.getLogger(__name__)


class Fetchmail(models.Model):
    _inherit = 'fetchmail.server'

    check_mailbox_size = fields.Boolean("Check Size")
    mailbox_size_partner_ids = fields.Many2many(
        "res.partner", string="Contacts to notify",
        domain=[('email', '!=', False)]
    )

    @api.model
    def _check_mailboxes_size_cron(self):
        """ Method called by cron to fetch mails from servers """
        return self.search([
            ('state', '=', 'done'),
            ('type', '=', 'imap'),
            ('check_mailbox_size', '=', True)
        ])._check_mailbox_size()

    @api.multi
    def _check_mailbox_size(self):
        for server in self:
            result_msg = ''
            imap_server = None
            try:
                if not server.mailbox_size_partner_ids:
                    continue
                result_msg += _('<h3>Server %s</h3>') % server.name
                _logger.info(
                    "Starting to check mailbox size for server %s"
                    % server.name)
                imap_server = server.connect()
                # The list of all folders
                result, list = imap_server.list()
                if result != "OK":
                    raise Exception(_("Server responded %s") % result)
                result_msg += _(
                    "<table>"
                    "<thead>"
                    "<tr>"
                    "<th style=\"text-align:left\">Folder</th>"
                    "<th style=\"text-align:right\"># Msg</th>"
                    "<th style=\"text-align:right\">Size</th>"
                    "</tr>"
                    "</thead>"
                    "<tbody>"
                )
                number_of_messages_all = 0
                size_all = 0
                for item in list:
                    x = item.split()
                    mailbox = x[-1]

                    # Select the desired folder
                    result, number_of_messages = imap_server.select(
                        mailbox, readonly=1)
                    if result != 'OK':
                        _logger.info(
                            "Server %s responded %s for folder %s"
                            % (server.name, number_of_messages, mailbox))
                        continue
                    number_of_messages_all += int(number_of_messages[0])

                    size_folder = 0
                    # Go through all the messages in the selected folder
                    typ, msg = imap_server.search(None, 'ALL')
                    # Find the first and last messages
                    m = [int(msg_part) for msg_part in msg[0].split()]
                    m.sort()
                    if m:
                        message_set = "%d:%d" % (m[0], m[-1])
                        result, sizes_response = imap_server.fetch(
                            message_set, "(UID RFC822.SIZE)")
                        for i in range(m[-1]):
                            tmp = sizes_response[i].split()
                            size_folder += int(tmp[-1].replace(')', ''))
                    else:
                        size_folder = 0
                    result_msg += (
                        "<tr>"
                        "<td style=\"text-align:left\">%s</td>"
                        "<td style=\"text-align:right\">%i</td>"
                        "<td style=\"text-align:right\">%s</td>"
                        "</tr>"
                    ) % (mailbox, int(number_of_messages[0]), size_folder)
                    size_all += size_folder

                result_msg += _(
                    "</tbody>"
                    "<tfoot>"
                    "<tr>"
                    "<td style=\"text-align:left;font-weight:bold\">Sum</td>"
                    "<td style=\"text-align:right;font-weight:bold\">%i</td>"
                    "<td style=\"text-align:right;font-weight:bold\">"
                    "%10.3fMB</td>"
                    "</tr>"
                    "</tfoot>"
                    "</table>"
                ) % (number_of_messages_all, size_all / 1e6)
            except Exception as e:
                result_msg = _(
                    "An error occured while checking mailbox %s:<br/>%s"
                ) % (server.name, str(e))
            finally:
                if imap_server:
                    imap_server.logout()
            if result_msg:
                self.env['mail.mail'].create({
                    'subject': _("Mailbox size for server %s") % server.name,
                    'body_html': result_msg,
                    'recipient_ids': [
                        (6, 0, server.mailbox_size_partner_ids.ids)]
                })

    @api.model
    def _update_cron(self):
        res = super(Fetchmail, self)._update_cron()
        if self.env.context.get('fetchmail_cron_running'):
            return res
        try:
            cron = self.env.ref(
                'mail_check_mailbox_size.ir_cron_check_mailbox_size')
            cron.toggle(model=self._name, domain=[
                ('state', '=', 'done'), ('type', '=', 'imap'),
                ('check_mailbox_size', '=', True),
            ])
        except ValueError:
            # Nevermind if ir_cron_check_mailbox_size cannot be found
            pass
        return res
