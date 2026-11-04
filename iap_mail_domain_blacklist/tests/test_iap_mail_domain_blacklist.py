# Copyright 2025 Quartile
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.tests import TransactionCase

from odoo.addons.iap.tools import iap_tools

from ..hooks import update_mail_domain_blacklist


class TestMailDomainBlacklist(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.config_param = cls.env["ir.config_parameter"]
        cls.predefined_domains = {"outlook.jp", "test.jp"}
        cls.original_blacklist = iap_tools._MAIL_DOMAIN_BLACKLIST.copy()

    @classmethod
    def tearDownClass(cls):
        iap_tools._MAIL_DOMAIN_BLACKLIST.clear()
        iap_tools._MAIL_DOMAIN_BLACKLIST.update(cls.original_blacklist)
        super().tearDownClass()

    def test_domains_blacklist(self):
        for domain in self.predefined_domains:
            self.assertNotIn(domain, iap_tools._MAIL_DOMAIN_BLACKLIST)
        self.config_param.set_param(
            "iap_mail_domain_blacklist.mail_domain_blacklist",
            ",".join(self.predefined_domains),
        )
        with self.env.cr.savepoint():
            update_mail_domain_blacklist(self.env.cr)
        for domain in self.predefined_domains:
            self.assertIn(domain, iap_tools._MAIL_DOMAIN_BLACKLIST)
