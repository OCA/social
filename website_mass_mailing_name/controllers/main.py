# -*- coding: utf-8 -*-
# © 2016 Jairo Llopis <jairo.llopis@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from openerp.addons.mass_mailing.controllers.main import MassMailController
from openerp.http import request, route


class MassMailingPartner(MassMailController):
    @route()
    def is_subscriber(self, *args, **kwargs):
        """Get user name too."""
        result = super(MassMailingPartner, self).is_subscriber(*args, **kwargs)
        email = result.get("email") or ""
        if request.website.user_id != request.env.user:
            name = request.env.user.name
        else:
            name, email = (request.env["mail.mass_mailing.contact"]
                           .get_name_email(email, context=request.context))
        result["name"] = name
        result["email"] = email
        return result
