# -*- coding: utf-8 -*-
# Copyright 2016-2017 Jairo Llopis <jairo.llopis@tecnativa.com>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo.addons.website_mass_mailing.controllers import main
from odoo.http import request, route


class MassMailController(main.MassMailController):
    @route()
    def is_subscriber(self, *args, **kwargs):
        """Get user name too."""
        result = super(MassMailController, self).is_subscriber(*args, **kwargs)
        if request.website.user_id != request.env.user:
            name = request.env.user.name
        else:
            name = request.session.get("mass_mailing_name", "")
        return dict(result, name=name)

    @route()
    def subscribe(self, list_id, email, **post):
        """Store email with name in session."""
        result = super(MassMailController, self).subscribe(
            list_id, email, **post)
        name, email = request.env['mail.mass_mailing.contact'].sudo() \
            .get_name_email(email)
        request.session["mass_mailing_name"] = name if name != email else ""
        return result
