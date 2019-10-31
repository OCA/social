# Copyright 2019 Tecnativa - Jairo Llopis
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.http import request, route
from odoo.addons.website_mass_mailing.controllers import main


class MassMailController(main.MassMailController):
    @route()
    def subscribe(self, list_id, email, **post):
        """Send welcome email to subscribers."""
        result = super().subscribe(list_id, email, **post)
        list_ = request.env["mail.mass_mailing.list"] \
            .sudo().browse(int(list_id))
        template = list_.welcome_mail_template_id
        if not template:
            return result
        # Welcome new subscribers
        contact_obj = request.env["mail.mass_mailing.contact"].with_context(
            default_list_ids=[list_id])
        contact = contact_obj.sudo().search([
            ('email', '=', request.session['mass_mailing_email']),
            ('opt_out', '=', False),    # Needed until odoo/odoo#39604 is fixed
            ('is_blacklisted', '=', False),
        ], limit=1)
        # Needed until odoo/odoo#39604 is fixed
        if not contact:
            return result
        template.with_context(list_name=list_.name).send_mail(
            contact.id,
            # Must send now to use context
            force_send=True,
            # If we cannot notify, the visitor shouldn't be bothered
            raise_exception=False,
        )
        return result
