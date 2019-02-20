# Copyright 2019 Eficent Business and IT Consulting Services, S.L.
# Copyright 2019 Aleph Objects, Inc.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
{
    "name": "Message Auto Subscribe Notify Own",
    "summary": "Receive notifications of your own subscriptions",
    "version": "11.0.2.0.0",
    "category": "Social Network",
    "website": "https://github.com/OCA/social",
    "author": "Eficent, "
              "Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "installable": True,
    "depends": [
        "mail",
    ],
    "data": [
        'security/ir.model.access.csv',
        'views/auto_subscribe_notify_own_model.xml'
    ]
}
