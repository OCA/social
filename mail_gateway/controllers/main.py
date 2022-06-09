from odoo import http
from odoo.http import request

from odoo.addons.mail.controllers.bus import MailChatController
from odoo.addons.mail.controllers.main import MailController


class NewMailController(MailController):
    @http.route("/mail/init_messaging", type="json", auth="user")
    def mail_init_messaging(self):
        result = super().mail_init_messaging()
        result["broker_slots"] = request.env["mail.broker"].broker_fetch_slot()
        return result


class NewMailChatController(MailChatController):
    def _poll(self, dbname, channels, last, options):
        if request.session.uid:
            if request.env.user.has_group("mail_broker.broker_user"):
                for bot in request.env["mail.broker"].search([]):
                    channels.append((request.db, "mail.broker", bot.id))
        return super()._poll(dbname, channels, last, options)
