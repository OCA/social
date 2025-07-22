# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import fields, models


class ResUsersSettings(models.Model):
    _inherit = "res.users.settings"

    is_discuss_sidebar_category_gateway_open = fields.Boolean(
        string="Gateway Category Open",
        default=True,
        help="The gateway category in the sidebar will be open",
    )
