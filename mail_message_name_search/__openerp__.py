# -*- coding: utf-8 -*-
# © 2016 Eficent Business and IT Consulting Services S.L.
#   (http://www.eficent.com)
# © 2016 Serpent Consulting Services Pvt. Ltd. (<http://www.serpentcs.com>)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

{
    "name": "Mail message name search",
    "version": "8.0.1.0.0",
    "author": "Eficent,"
              "SerpentCS,"
              "Odoo Community Association (OCA)",
    "website": "http://www.eficent.com",
    "category": "Social",
    "data": ["data/trgm_index_data.xml",
             "views/trgm_index_view.xml"],
    "depends": ["base", "mail",
                "base_search_fuzzy"],
    "license": "AGPL-3",
    'installable': True,
}
