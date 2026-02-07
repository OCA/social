# Copyright 2026 nurefexc (https://nurefexc.com)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo.tests.common import TransactionCase


class TestNtfyUrl(TransactionCase):

    def setUp(self):
        super(TestNtfyUrl, self).setUp()
        # Létrehozunk egy teszt felhasználót
        self.test_user = self.env['res.users'].create({
            'name': 'Test Ntfy User',
            'login': 'test_ntfy_user',
            'email': 'test@nurefexc.com',
            'notification_type': 'inbox',  # Alapértelmezett
        })
        # Alapértelmezett ntfy szerver beállítása
        self.env['ir.config_parameter'].sudo().set_param('ntfy.server_url', 'https://ntfy.sh')

    def test_01_url_generation_on_write(self):
        """Teszteljük, hogy az URL legenerálódik, ha átváltunk ntfy-ra"""
        self.test_user.write({'notification_type': 'ntfy'})

        self.assertTrue(self.test_user.ntfy_topic_url, "Az URL-nek nem szabadna üresnek lennie!")
        self.assertIn('https://ntfy.sh', self.test_user.ntfy_topic_url)
        self.assertIn(str(self.test_user.id), self.test_user.ntfy_topic_url)

    def test_02_action_regenerate_url(self):
        """Teszteljük a manuális regenerálást (Reset gomb)"""
        self.test_user.write({'notification_type': 'ntfy'})
        first_url = self.test_user.ntfy_topic_url

        # Akció meghívása (mintha a frissítés ikonra kattintanánk)
        self.test_user.action_generate_ntfy_url()
        second_url = self.test_user.ntfy_topic_url

        self.assertNotEqual(first_url, second_url, "Az URL-nek meg kellene változnia regenerálás után!")

    def test_03_server_url_change_sync(self):
        """Teszteljük, hogy a rendszer észreveszi-e a szervercím változását"""
        self.test_user.write({'notification_type': 'ntfy'})

        # Szervercím módosítása a rendszerbeállításokban
        self.env['ir.config_parameter'].sudo().set_param('ntfy.server_url', 'https://ntfy.nurefexc.com')

        # A mail_thread hook vagy a consistency check meghívása
        self.test_user._check_ntfy_url_consistency()

        self.assertIn('https://ntfy.nurefexc.com', self.test_user.ntfy_topic_url)
