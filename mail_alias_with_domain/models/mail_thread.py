# Copyright 2023 Solvti sp. z o.o. (https://solvti.pl)

import logging

from odoo import api, models, tools

from .mail_alias import generate_hash

_logger = logging.getLogger(__name__)


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    @api.model
    def message_route(
        self, message, message_dict, model=None, thread_id=None, custom_values=None
    ):
        """ Prepare message_dict by extending recipients
            with found aliases mails base on alias and domain
        """
        try:
            maching_aliases = self._find_alias_with_domain(message_dict)
            if maching_aliases:
                recipients = (
                    f"{message_dict['recipients']},"
                    f"{','.join(maching_aliases.mapped('display_name'))}"
                )
                message_dict["recipients"] = recipients
        except Exception as e:
            _logger.error(f"Unexpected error during processing alias with domain: {e}")
        return super().message_route(
            message, message_dict, model, thread_id, custom_values
        )

    def _find_alias_with_domain(self, message_dict):
        emails = {email for email in (tools.email_split(message_dict["recipients"]))}
        hash_list = list(
            map(generate_hash, [email.replace("@", "") for email in emails])
        )
        match = self.env["mail.alias"].search(
            [("check_domain", "=", True), ("alias_hash", "in", hash_list)]
        )
        return match
