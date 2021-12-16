Create the bot
~~~~~~~~~~~~~~

1. Create a Bot on telegram https://core.telegram.org/bots
2. Create a broker following the examples on
   https://github.com/tegin/telegram-broker with the TOKEN provided


Configure Odoo
~~~~~~~~~~~~~~

1. Access on debug mode
2. Access `Settings > Technical Settings > Email > Mail Broker`.
3. Create a bot and assign the token. Mark it as `Show on App`
4. Press on `Generate webhook` in order to Open the webhook

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
