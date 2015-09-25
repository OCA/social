# -*- coding: utf-8 -*-
# © 2015 Antiun Ingeniería S.L. (http://www.antiun.com)
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from openerp import http
from openerp.addons.mass_mailing.controllers.main import MassMailController


class CustomUnsuscribe(MassMailController):
    @http.route()
    def mailing(self, *args, **kwargs):
        path = "/page/mass_mail_unsubscription_%s"
        result = super(CustomUnsuscribe, self).mailing(*args, **kwargs)
        return http.local_redirect(
            path % ("success" if result.data == "OK" else "failure"))
