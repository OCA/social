# Copyright 2023 Foodles (https://www.foodles.com/)
# @author Pierre Verkest <pierreverkest84@gmail.com>
# @author Matthias Barkat <matthias.barkat@foodles.co>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
{
    "name": "Mail Contact Type",
    "summary": "Mail Contact Type",
    "version": "14.0.1.0.0",
    "development_status": "Alpha",
    "category": "Productivity/Discuss",
    "website": "https://github.com/OCA/social",
    "author": "Foodles, Odoo Community Association (OCA)",
    "maintainers": ["petrus-v"],
    "license": "AGPL-3",
    "depends": [
        "contacts",
        "mail",
        "base_view_inheritance_extension",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/mail_compose_message_view.xml",
        "views/mail_contact_type.xml",
        "views/res_partner.xml",
        "views/menu.xml",
    ],
    "installable": True,
}
