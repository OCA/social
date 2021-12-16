# Copyright 2021 Creu Blanca
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import logging

from odoo import fields, models

_logger = logging
try:
    import telegram
except (ImportError, IOError) as err:
    _logger.debug(err)


class MailBroker(models.Model):

    _inherit = "mail.broker"

    telegram_security_key = fields.Char()
    broker_type = fields.Selection(selection_add=[("telegram", "Telegram")])

    def _get_telegram_bot(self):
        return telegram.Bot(self.token)

    def _set_webhook(self):
        bot = self._get_telegram_bot()
        bot.setWebhook(url=self._get_webhook_url())
        super(MailBroker, self)._set_webhook()

    def _remove_webhook(self):
        bot = self._get_telegram_bot()
        webhookinfo = bot.get_webhook_info()
        if webhookinfo.url:
            bot.delete_webhook(drop_pending_updates=False)
        super(MailBroker, self)._remove_webhook()

    def _get_channel_vals(self, token, update):
        result = super(MailBroker, self)._get_channel_vals(token, update)
        if self.broker_type == "telegram":
            names = []
            for name in [
                update.message.chat.first_name or False,
                update.message.chat.last_name or False,
                update.message.chat.description or False,
                update.message.chat.title or False,
            ]:
                if name:
                    names.append(name)
            result["name"] = " ".join(names)
        return result

    def _preprocess_update_telegram(self, update):
        for entity in update.message.entities:
            if not entity.offset == 0:
                continue
            if not entity.type == "bot_command":
                continue
            command = update.message.parse_entity(entity).split("/")[1]
            if hasattr(self, "_command_telegram_%s" % (command)):
                return getattr(self, "_command_telegram_%s" % (command))(update)
        return False

    def _command_telegram_start(self, update):
        if (
            not self.has_new_channel_security
            or update.message.text == "/start %s" % self.telegram_security_key
        ):
            return self._get_channel(update.message.chat_id, update, True)
        return True

    def _receive_update_telegram(self, update):
        telegram_update = telegram.Update.de_json(update, self._get_telegram_bot())
        if self._preprocess_update_telegram(telegram_update):
            return
        chat = self._get_channel(telegram_update.message.chat_id, telegram_update)
        if not chat:
            return
        return chat.telegram_update(telegram_update)
