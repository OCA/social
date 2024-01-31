Create the bot
~~~~~~~~~~~~~~

1. Create a Bot on telegram https://core.telegram.org/bots
2. Create a broker following the examples on
   https://github.com/tegin/telegram-broker with the TOKEN provided


Configure Odoo
~~~~~~~~~~~~~~

1. Access on debug mode
2. Access `Settings > Technical Settings > Email > Mail Gateway`.
3. Access Telegram and start a converstation with BotFather.
4. Create a bot using the command /newbot. The system will ask for a bot name. Remember that it needs to end with the word bot.
5. Copy the token to access the HTTP API to the token field.
6. Define Webhook key an webhook secret of your choice in its corresponding field, in order to secure the connection.
7. Press save button and the integrate webhook smart button will appear.
8. Press the Integrate webhook button.
9. If you want to add an extra layer of security, you can check Has New Channel Security and define a Telegram security key. New chats will be created only with the command /start SECURITY_KEY.

Limitations
~~~~~~~~~~~

The Webhook functionality can only be used if your system is accessible from website.
On local installations it might be problematic as Telegram will not be able to contact
your system. In that case, you might need to create a telegram bot that will send data
to you on an external process with the following code.

.. code-block:: python

    from telegram.ext import Filters, MessageHandler, Updater
    import requests
    dp = Updater(YOUR_TOKEN)

    def message_callback(update, _context):
        requests.post(YOUR_CONTROLLER, json=update.to_dict())


    dp.dispatcher.add_handler(MessageHandler(Filters.all, message_callback))
    dp.start_polling()
    dp.idle()
