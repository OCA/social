# Copyright 2019 Therp BV <https://therp.nl>
# Copyright 2022 Opener B.V. <stefan@opener.amsterdam>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from mock import patch

from odoo.tests import TransactionCase

from odoo.addons.base.models.ir_mail_server import IrMailServer


class TestMailDataLink(TransactionCase):
    def test_mail_data_link(self):
        """Test if internal data links are replaced by absolute URIs"""
        user_demo = self.env.ref("base.user_demo")
        user_demo.notification_type = "email"
        partner = user_demo.partner_id
        body = f"""
        <div>
            <a href='#' data-oe-model={partner._name} data-oe-id={partner.id}>
                test
            </a>
        </div>
        """

        def _test_mail(email, *args, **kwargs):
            base_url = self.env["ir.config_parameter"].get_param("web.base.url")
            partner = self.env.ref("base.user_demo").partner_id
            url = f"{base_url}/mail/view?model=res.partner&amp;res_id={partner.id}"
            for part in email.walk():
                if part.get_content_type() == "text/html":
                    body = part.get_content()
                    self.assertIn(f'href="{url}"', body)
                    break
            return False

        with patch.object(IrMailServer, "send_email", side_effect=_test_mail):
            partner.message_post(body=body, partner_ids=partner.ids)
