# Copyright 2025 Hunki Enterprises BV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl-3.0)

from odoo import api, fields, models


class MicrosoftOutlookMixin(models.AbstractModel):
    _inherit = "microsoft.outlook.mixin"

    microsoft_outlook_client_id = fields.Char(
        string="Outlook Client ID",
        help="If you want to use a different account than the globally "
        "configured one, fill in its client id here",
        groups="base.group_system",
        copy=False,
    )
    microsoft_outlook_client_secret = fields.Char(
        string="Outlook Client secret",
        help="If you want to use a different account than the globally "
        "configured one, fill in its client secret here",
        groups="base.group_system",
        copy=False,
    )

    @api.depends("microsoft_outlook_client_id", "microsoft_outlook_client_secret")
    def _compute_is_microsoft_outlook_configured(
        self,
    ):  # pylint: disable=missing-return
        for this in self:
            super(
                MicrosoftOutlookMixin,
                this.with_context(microsoft_outlook_multi_token=this),
            )._compute_is_microsoft_outlook_configured()

    def _compute_outlook_uri(self):  # pylint: disable=missing-return
        for this in self:
            super(
                MicrosoftOutlookMixin,
                this.with_context(microsoft_outlook_multi_token=this),
            )._compute_outlook_uri()

    @api.onchange("microsoft_outlook_client_id", "microsoft_outlook_client_secret")
    def _onchange_microsoft_outlook_multi_token(self):
        self.update(
            dict(
                microsoft_outlook_refresh_token=False,
                microsoft_outlook_access_token=False,
                microsoft_outlook_access_token_expiration=False,
            )
        )

    def _fetch_outlook_token(self, grant_type, **values):
        self = self.with_context(microsoft_outlook_multi_token=self)
        return super()._fetch_outlook_token(grant_type, **values)
