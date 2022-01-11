# Copyright 2016-2017 Jairo Llopis <jairo.llopis@tecnativa.com>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo.http import request, route

from odoo.addons.website_mass_mailing.controllers import main


class MassMailController(main.MassMailController):
    @route()
    def is_subscriber(self, list_id, **post):
        """Get user name too."""
        result = super().is_subscriber(list_id, **post)
        if request.website.user_id != request.env.user:
            name = request.env.user.name
        else:
            name = request.session.get("mass_mailing_name", "")
        return dict(result, name=name)

    @route()
    def subscribe(self, list_id, email, **post):
        """Store email with name in session."""
        result = super().subscribe(list_id, email, **post)
        name, email = request.env["mailing.contact"].sudo().get_name_email(email)
        request.session["mass_mailing_name"] = name if name != email else ""
        return result
