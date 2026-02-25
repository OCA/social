# Copyright 2026 Therp BV <https://therp.nl>.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
"""We override the standard functionality that only supports one Outlook connection.

To support each outgoing or incoming mail server to have its own connection to Outlook,
we provide for the connection parameters to be part of the server definition itself.

If there is no connection information in the server record, we will still fall back to
the default configuration using system parameters.
"""

from odoo import api, fields, models


class MicrosoftOutlookMixin(models.AbstractModel):
    """Extend standard mixin, that will also be used for fetchmail."""

    _inherit = "microsoft.outlook.mixin"

    microsoft_outlook_client_identifier = fields.Char(
        "Outlook Client Id",
        help="Specific client_id for this server",
    )
    microsoft_outlook_client_secret = fields.Char(
        "Outlook Client Secret",
        help="Specific client_secret for this server",
    )

    @api.depends(
        "use_microsoft_outlook_service",
        "microsoft_outlook_client_identifier",
        "microsoft_outlook_client_secret",
    )
    def _compute_is_microsoft_outlook_configured(self):
        """Check using this record, else fallback to default.

        The field microsoft_outlook_configured should be set to
        true when client identifier and secret have been set. The
        values for these fields must be given by the person who
        registered the Odoo tenant in the Azure directory.
        """
        # Cannot depend on trick to override get_param as original
        # method might fail on Singleton error.
        for this in self:
            if not this.use_microsoft_outlook_service:
                # The super method also returns True for any record, whether configured
                # to use Outlook or not, if system parameters for outlook have been set.
                # This is pure madness, so we override this.
                self.is_microsoft_outlook_configured = False
            elif this._has_id_and_secret():
                self.is_microsoft_outlook_configured = True
            else:
                super(
                    MicrosoftOutlookMixin, this
                )._compute_is_microsoft_outlook_configured()

    @api.depends(
        "use_microsoft_outlook_service",
        "microsoft_outlook_client_identifier",
        "microsoft_outlook_client_secret",
    )
    def _compute_outlook_uri(self):
        """The outlook_uri contains the information that is needed activate the client.

        After client id and secret have been set, the user must click on the
        "Connect Your Outlook account" button. This will open a Microsoft
        webpage containing the needed information. Microsoft will then
        generate an authorization token and call back a controller that sets
        this token, and a refresh token and expiration on the server record.
        """
        record = self._get_preset_record() if self._has_id_and_secret() else self
        return super(MicrosoftOutlookMixin, record)._compute_outlook_uri()

    def _fetch_outlook_refresh_token(self, authorization_code):
        record = self._get_preset_record() if self._has_id_and_secret() else self
        return super(MicrosoftOutlookMixin, record)._fetch_outlook_refresh_token(
            authorization_code
        )

    def _has_id_and_secret(self):
        """Check whether called on record with specific client ID and Secret."""
        if (
            len(self) == 1
            and self.microsoft_outlook_client_identifier
            and self.microsoft_outlook_client_secret
        ):
            return True
        return False

    def _get_preset_record(self):
        """Return record with context filled with preset client id and secret."""
        self.ensure_one()
        return self.with_context(
            preset_microsoft_outlook_client_id=self.microsoft_outlook_client_identifier,
            preset_microsoft_outlook_client_secret=self.microsoft_outlook_client_secret,
        )
