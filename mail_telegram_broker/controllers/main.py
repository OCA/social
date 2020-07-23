from odoo import http
from odoo.http import request
from odoo.addons.mail.controllers.main import MailController
from odoo.addons.mail.controllers.bus import MailChatController


class NewMailController(MailController):

    @http.route('/mail/init_messaging', type='json', auth='user')
    def mail_init_messaging(self):
        result = super().mail_init_messaging()
        result['telegram_slots'] = request.env['mail.telegram.bot'].bot_fetch_slot()
        return result


class NewMailChatController(MailChatController):
    def _poll(self, dbname, channels, last, options):
        if request.session.uid:
            if request.env.user.has_group('mail_telegram_broker.telegram_user'):
                for bot in request.env['mail.telegram.bot'].search([]):
                    channels.append((request.db, 'mail.telegram.bot', bot.id))
        return super()._poll(dbname, channels, last, options)
