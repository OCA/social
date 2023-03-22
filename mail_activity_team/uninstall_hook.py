from odoo import SUPERUSER_ID, api


def uninstall_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    rule = env.ref("calendar.calendar_event_rule_private", raise_if_not_found=False)
    if rule:
        rule.write(
            {
                "name": "Private events",
                "domain_force": "['|', "
                "('privacy', '!=', 'private'),"
                "'&', ('privacy', '=', 'private'),"
                "('partner_ids', 'in', user.partner_id.id)]",
            }
        )
