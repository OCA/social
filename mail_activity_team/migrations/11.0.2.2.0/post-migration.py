#  Copyright 2019 Tecnativa - Sergio Teruel
#  License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl
from openupgradelib import openupgrade


@openupgrade.migrate(use_env=True)
def migrate(env, version):
    rule = env.ref('calendar.calendar_event_rule_private')
    rule.write({
        'name': 'Private or group events',
        'domain_force': "['|', '|', "
                        "('privacy', 'not in', ['private', 'team']),"
                        "'&', ('privacy', '=', 'private'),"
                        "('partner_ids', 'in', user.partner_id.id),"
                        "'&', ('privacy', '=', 'team'),"
                        "('team_id', 'in', user.activity_team_ids.ids)]"
    })
