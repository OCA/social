# Copyright 2023 Solvti sp. z o.o. (https://solvti.pl)
# Copyright 2025 Therp BV (https://therp.nl)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from odoo import api, models, tools


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    @api.model
    def message_route(
        self, message, message_dict, model=None, thread_id=None, custom_values=None
    ):
        """Check for a recipient that can be linked to a full domain alias."""
        if not self.env.context.get("matching_alias", False):
            matching_alias = self._find_alias_with_domain(message_dict)
            if matching_alias:
                # Call super with extra context.
                return (
                    super()
                    .with_context(matching_alias=matching_alias)
                    .message_route(
                        message,
                        message_dict,
                        model=model,
                        thread_id=thread_id,
                        custom_values=custom_values,
                    )
                )
        return super().message_route(
            message,
            message_dict,
            model=model,
            thread_id=thread_id,
            custom_values=custom_values,
        )

    def _find_alias_with_domain(self, message_dict):
        """Find all aliasses that match."""
        Alias = self.env["mail.alias"]
        emails = {email for email in (tools.email_split(message_dict["recipients"]))}
        alias_names = []
        for email in emails:
            clean_email = Alias.get_clean_email(email)
            if not clean_email:
                continue
            alias_name = clean_email.replace("@", "__at__")
            alias_names.append(alias_name)
        return Alias.search([("alias_name", "in", alias_names)])
