# Copyright 2020 Simone Orsi - Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

from odoo import http
from odoo.http import request


class Preview(http.Controller):

    _list_template = "mail_layout_preview.email_templates_list"

    @http.route(
        ["/email-preview/<string:model>"], type="http", auth="user", website=True
    )
    def template_list(self, model, **kw):
        env = request.env
        templates = env["mail.template"].search([("model_id.model", "=", model)])
        xids = templates.get_external_id()
        return request.render(
            self._list_template, {"model": model, "templates": templates, "xids": xids}
        )

    @http.route(
        ["/email-preview/<string:model>/<string:templ_id>/<int:rec_id>"],
        type="http",
        auth="user",
        website=True,
    )
    def preview(self, model, templ_id, rec_id, **kw):
        """Render an email template to verify look and feel.

        Provide model, record id and an email template to render.

        Example for event registration email:

        /email-preview/event.registration/event.event_subscription/5
        """
        env = request.env
        record = env[model].browse(rec_id)
        if templ_id.isdigit():
            # got an ID
            template = env["mail.template"].browse(int(templ_id))
        else:
            # got a XID
            template = env.ref(templ_id.strip())
        result = template.generate_email(record.id)
        return request.make_response(result["body_html"])
