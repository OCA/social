# -*- coding: utf-8 -*-
# Copyright 2017 Eficent Business and IT Consulting Services S.L.
#   (http://www.eficent.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

{
    "name": "Mail Auto Follower Notify",
    "summary": "This module extends the functionality of mail by sending an "
               "email notification to new followers that are system users",
    "author": "Eficent, "
              "Odoo Community Association (OCA)",
    "website": "https://odoo-community.org/",
    "category": "Mail",
    "depends": ["mail", "base_patch_models_mixin"],
    "license": "AGPL-3",
    'installable': True,
    'application': False,
}
