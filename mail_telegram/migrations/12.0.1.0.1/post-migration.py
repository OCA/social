# Copyright 2020 Creu Blanca
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade


@openupgrade.migrate()
def migrate(env, version):
    env.cr.execute("SELECT id, token FROM mail_telegram_chat WHERE not bot_id")
    tokens = {}
    for data in env.cr.fetchall():
        if data['token'] not in tokens:
            tokens[data['token']] = env['mail.telegram.bot'].create({
                'name': data['token'],
                'token': data['token'],
            })
        env['mail.telegram.chat'].browse(data['id']).write({
            'bot_id': tokens[data['token']].id
        })
