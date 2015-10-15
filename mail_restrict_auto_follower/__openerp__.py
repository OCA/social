# -*- coding: utf-8 -*-
# (c) 2015 Serv. Tecnol. Avanzados - Pedro M. Baeza
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html
{
    "name": "Restrict automatic follower subscription",
    "version": "8.0.1.0.0",
    "author": "Serv. Tecnol. Avanzados - Pedro M. Baezza,"
              "Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "category": "Social Network",
    "summary": "Set a domain to restrict the automatic follower subscription",
    "depends": [
        'mail',
    ],
    "data": [
        "data/ir_config_parameter.xml",
        "data/ir_actions.xml",
    ],
    "installable": True,
}
