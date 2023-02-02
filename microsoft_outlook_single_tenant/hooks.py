# Copyright 2022 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import logging

_logger = logging.getLogger(__name__)


def deprecate():
    _logger.warning(
        """
        `microsoft_outlook_single_tenant` is deprecated.
        Configure microsoft_outlook.endpoint ir.config_parameter
        """
    )


def post_load_hook():
    deprecate()
