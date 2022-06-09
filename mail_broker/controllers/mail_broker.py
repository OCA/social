# Copyright 2018 ACSONE SA/NV
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo.addons.base_rest.controllers import main


class MailBrokerController(main.RestController):
    _root_path = "/broker/"
    _collection_name = "mail.broker.services"
    _default_auth = "none"
