# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    if not version:
        return

    env = api.Environment(cr, SUPERUSER_ID, {})
    body_type = env["ir.model.fields"].search(
        [("name", "=", "body_type"), ("model", "=", "mail.template")]
    )

    # Note: no need to migrate the existing values of the `body_type` of the
    #   model `mail_template` because Odoo already does it
    #   See https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/models/ir_model.py#L1351
    if body_type:
        # qweb -> qweb_view
        qweb = env["ir.model.fields.selection"].search(
            [("value", "=", "qweb"), ("field_id", "=", body_type.id)]
        )
        qweb.write({"value": "qweb_view"})

        # jinja2 -> qweb
        jinja = env["ir.model.fields.selection"].search(
            [("value", "=", "jinja2"), ("field_id", "=", body_type.id)]
        )
        jinja.write({"value": "qweb"})
