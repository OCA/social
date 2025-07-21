# Copyright 2022-2023 Moduon Team S.L. <info@moduon.team>
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
import logging

_logger = logging.getLogger(__name__)


def post_init_hook(env):
    """Increase cadence of mail queue cron."""
    try:
        cron = env.ref("mail.ir_cron_mail_scheduler_action")
    except ValueError:
        _logger.warning(
            "Couldn't find the standard mail scheduler cron. "
            "Maybe no mails will be ever sent!"
        )
    else:
        _logger.info("Setting mail queue cron cadence to 1 minute")
        cron.interval_number = 1
        cron.interval_type = "minutes"
