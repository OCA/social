# -*- coding: utf-8 -*-
# © 2016 Diagram Software S.L.
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html
{
    'name': "Pinterest Social Media Icon Extension",
    'summary': """Pinterest Extension for the social media icons from the
    odoo core""",
    'author': "Diagram Software S.L., Odoo Community Association (OCA)",
    'website': "http://www.diagram.es",
    'license': 'AGPL-3',
    'category': 'Social Media',
    'version': '8.0.1.0.0',
    'depends': [
        'website',
    ],
    'data': [
        'views/website_templates.xml',
        'views/website_views.xml',
        'views/res_config.xml',
    ],
}
