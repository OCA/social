# Copyright 2022 CreuBlanca
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.addons.component.tests.common import SavepointComponentRegistryCase


class MailBrokerComponentRegistryTestCase(SavepointComponentRegistryCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._setup_env()
        cls._load_module_components(cls, "mail_broker")

    @classmethod
    def _setup_context(cls):
        return dict(
            cls.env.context, tracking_disable=True, test_queue_job_no_delay=True
        )

    @classmethod
    def _setup_env(cls):
        cls.env = cls.env(context=cls._setup_context())
